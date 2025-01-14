import os
import re
import sys
from pathlib import Path
from typing import cast, Iterable, List, Tuple

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from xonsh.built_ins import XSH

from xonsh.completers.completer import add_one_completer, RichCompletion
from xonsh.completers.tools import (
    CompleterResult,
    CompletionContext,
    contextual_completer,
    non_exclusive_completer,
)

from kmd.commands.help_commands import HELP_COMMANDS
from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_COMMAND, EMOJI_TASK, STYLE_ACTION_TEXT, STYLE_COMMAND_TEXT
from kmd.docs.faq_headings import faq_headings
from kmd.errors import InvalidState
from kmd.exec.system_actions import assistant_chat
from kmd.help.function_param_info import annotate_param_info
from kmd.model.params_model import Param
from kmd.model.paths_model import fmt_store_path
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import items_matching_precondition
from kmd.shell_ui.shell_syntax import assist_request_str, is_valid_command
from kmd.util.format_utils import single_line
from kmd.util.log_calls import log_calls
from kmd.util.type_utils import not_none
from kmd.workspaces.workspaces import current_ignore, current_workspace
from kmd.xonsh_customization.completion_ranking import (
    normalize,
    score_items,
    score_paths,
    score_phrase,
    score_subphrase,
    select_hits_by_score,
)

log = get_logger(__name__)

MAX_COMPLETIONS = 500

MAX_DIR_COMPLETIONS = 100

# We want to keep completion fast, so make it obvious when it's slow.
SLOW_COMPLETION = 0.15


def is_assist_request(context: CompletionContext) -> bool:
    """
    Check if this is an NL assistant request, based on whether it
    starts with a space or `?`:

    `<space>some question or request`
    `?some question or request`
    `? some question or request`
    """
    command = context.command
    if not command:
        return False

    arg_index = command.arg_index
    prefix = command.prefix.lstrip()

    return (
        (arg_index == 0 and (prefix.startswith(" ")))
        or (arg_index == 0 and prefix.startswith("?"))
        or (arg_index >= 1 and command.args[0].value.strip().startswith("?"))
    )


def _dir_description(directory: Path) -> str:
    if not directory.exists():
        return ""
    # TODO: Cache, maybe also track size and other info.
    count = sum(1 for _ in directory.glob("*"))
    return f"{count} files"


def _question_completions(
    context: CompletionContext, include_bare_qm: bool
) -> List[RichCompletion]:
    prefix_len = len(context.command and context.command.text_before_cursor or "") + 1

    completions = [
        RichCompletion(
            assist_request_str(question),
            display=question.lstrip("? "),
            prefix_len=prefix_len,
        )
        for question in faq_headings()
    ]

    completions.extend(
        [
            RichCompletion(
                command.__name__,
                display=f"{command.__name__} {EMOJI_COMMAND}",
                description=single_line(command.__doc__ or ""),
                style=STYLE_COMMAND_TEXT,
                append_space=True,
                prefix_len=prefix_len,
            )
            for command in HELP_COMMANDS
        ]
    )

    # A completion for a bare `?` to ask a question.
    if include_bare_qm:
        completions.insert(
            0,
            RichCompletion(
                "?",
                display="?",
                description="Ask for assistance.",
                prefix_len=prefix_len,
            ),
        )

    return completions


def _completion_matches(
    query: str, values: Iterable[str | RichCompletion], match_partial: bool = False
) -> List[RichCompletion]:
    """
    Tighter match for command completions.
    """
    matches = []

    for value in values:
        completion = value if isinstance(value, RichCompletion) else RichCompletion(value)
        normalized_value = normalize(str(completion.value))

        if (
            normalized_value.startswith(query)
            or score_phrase(query, normalized_value) > 90
            or (
                match_partial
                and len(normalized_value.split()) > 5
                and score_subphrase(query, normalized_value) > 90
            )
        ):
            matches.append(completion)

    return matches


@log_calls(level="debug")
def _command_completions(prefix: str) -> set[RichCompletion]:
    from kmd.xonsh_customization.kmd_init import _actions, _commands

    prefix = normalize(prefix)

    command_matches = _completion_matches(prefix, [c.__name__ for c in _commands.values()])
    command_completions = [
        RichCompletion(
            name,
            display=f"{name} {EMOJI_COMMAND}",
            description=single_line(_commands[name].__doc__ or ""),
            style=STYLE_COMMAND_TEXT,
            append_space=True,
        )
        for name in command_matches
    ]

    action_matches = _completion_matches(prefix, [a.name for a in _actions.values()])
    action_completions = [
        RichCompletion(
            name,
            display=f"{name} {EMOJI_TASK}",
            description=single_line(_actions[name].description or ""),
            style=STYLE_ACTION_TEXT,
            append_space=True,
        )
        for name in action_matches
    ]

    # input_empty = not prefix.strip()
    # help_completions = _completion_matches(prefix, _all_help_completions(input_empty))

    all_completions = command_completions + action_completions  # + help_completions
    all_completions.sort(key=completion_sort)

    return set(all_completions)


@log_calls(level="debug")
def _dir_completions(prefix: str, base_dir: Path) -> List[RichCompletion]:
    prefix = normalize(prefix)

    is_ignored = current_ignore()
    dirs = (d.relative_to(base_dir) for d in base_dir.iterdir() if d.is_dir() and not is_ignored(d))
    scored_paths = score_paths(prefix, dirs)

    hits = select_hits_by_score(scored_paths, min_score=60, max_hits=MAX_DIR_COMPLETIONS)

    log.debug(
        "Found %s dir hits out of %s completions.",
        len(hits),
        len(scored_paths),
    )
    # log.info("Dir hits: %s", fmt_lines([f"{s}: {p}" for s, p in hits]))

    return [
        RichCompletion(
            fmt_store_path(d) + "/",
            display=fmt_store_path(d),
            description=_dir_description(d),
            append_space=False,
        )
        for (score, d) in hits
    ]


@log_calls(level="debug")
def _item_completions(
    prefix: str,
    precondition: Precondition = Precondition.always,
    complete_from_sandbox: bool = True,
) -> List[RichCompletion] | None:
    prefix = normalize(prefix.lstrip("@"))

    ws = current_workspace()
    if ws.is_sandbox and not complete_from_sandbox:
        return None

    # Get immediate subdirectories from workspace base directory
    dir_completions = _dir_completions(prefix, ws.base_dir)

    starts_with_prefix = Precondition(
        lambda item: normalize(str(not_none(item.store_path))).startswith(prefix)
    )

    matching_items = list(
        items_matching_precondition(
            ws, precondition & starts_with_prefix, max_results=MAX_COMPLETIONS
        )
    )

    log.debug("Found %s items matching: %r", len(matching_items), prefix)

    scored_items = score_items(prefix, matching_items)

    hits = select_hits_by_score(scored_items, min_score=0, max_hits=MAX_COMPLETIONS)

    log.debug(
        "Found %s item hits out of %s completions.",
        len(hits),
        len(scored_items),
    )
    # log.info("Item hits: %s", fmt_lines([f"{s}: {item.store_path}" for s, item in hits]))

    # Don't show completions if there are too many matches.
    item_completions = []
    if len(hits) < MAX_COMPLETIONS:
        item_completions = [
            RichCompletion(
                fmt_store_path(not_none(item.store_path)),
                display=f"{fmt_store_path(not_none(item.store_path))} ({precondition.name}) ",
                description=item.title or "",
                append_space=True,
            )
            for (score, item) in hits
        ]
        log.debug("Found %s item completions", len(item_completions))
    else:
        log.debug("Too many items (%s) to offer completions, skipping.", len(matching_items))

    return dir_completions + item_completions


def completion_sort(completion: RichCompletion) -> Tuple[int, str]:
    return (len(completion.value), completion.value)


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def command_or_action_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes command names. We don't complete on regular shell commands to keep it cleaner.
    """

    if context.command and context.command.arg_index == 0:
        prefix = context.command.prefix
        completions = _command_completions(prefix)
        if len(completions) > 0:
            # If we have command matches, don't overdo it with more help completions too.
            return cast(CompleterResult, completions)
        else:
            # No command results, so fall back to help questions.
            return help_question_completer(context)

    return None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """
    from kmd.xonsh_customization.kmd_init import _actions

    try:
        if context.command and context.command.arg_index >= 1:
            action_name = context.command.args[0].value
            action = _actions.get(action_name)
            prefix = context.command.prefix
            if action and action.precondition:
                item_completions = _item_completions(prefix, action.precondition)
                return set(item_completions) if item_completions else None
    except InvalidState:
        return None
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def at_prefix_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes items in the current workspace if prefixed with '@' sign.
    """
    try:
        if context.command:
            prefix = context.command.prefix
            if prefix.startswith("@"):
                prefix = prefix.lstrip("@")
                if context.command.arg_index >= 1:
                    item_completions = _item_completions(prefix)
                    return set(item_completions) if item_completions else None
                else:
                    command_completions = _command_completions(prefix)
                    return set(command_completions) if command_completions else None

    except InvalidState:
        return None
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def help_question_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest help questions after a `?` on the command line.
    """
    if context.command:
        if is_assist_request(context):
            query = context.command.prefix.lstrip("? ")
            return set(
                _completion_matches(query, _question_completions(context, True), match_partial=True)
            )
    return None


def _param_completions(params: List[Param], prefix: str):
    return [
        RichCompletion(
            param.shell_prefix,
            description=param.description or "",
            append_space=(param.type == bool),
        )
        for param in params
        if param.shell_prefix.startswith(prefix)
    ]


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def options_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest options completions after a `-` or `--` on the command line.
    """
    from kmd.xonsh_customization.kmd_init import _actions, _commands

    if context.command and context.command.arg_index > 0:
        prefix = context.command.prefix

        is_option = prefix.startswith("-")

        command_name = context.command.args[0].value

        command = _commands.get(command_name)
        action = _actions.get(command_name)

        if is_option:
            completions = []
            help_text = ""
            params: List[Param] = []

            if command:
                help_text = "Show more help for this command."
                params = annotate_param_info(command)
            elif action:
                help_text = "Show more help for this action."
                params = list(action.params)

            completions = _param_completions(params, prefix)

            if completions and "--help".startswith(prefix):
                completions.append(RichCompletion("--help", description=help_text))

            return set(completions) if completions else None


# FIXME: Complete enum values for enum options.


@Condition
def is_unquoted_assist_request():
    app = get_app()
    buf = app.current_buffer
    text = buf.text.strip()
    is_default_buffer = buf.name == "DEFAULT_BUFFER"
    has_prefix = text.startswith("?") and not (text.startswith('? "') or text.startswith("? '"))
    return is_default_buffer and has_prefix


_command_regex = re.compile(r"^[a-zA-Z0-9_-]+$")

_python_keyword_regex = re.compile(
    r"assert|async|await|break|class|continue|def|del|elif|else|except|finally|"
    r"for|from|global|if|import|lambda|nonlocal|pass|raise|return|try|while|with|yield"
)


def _extract_command_name(text: str) -> str | None:
    text = text.split()[0]
    if _python_keyword_regex.match(text):
        return None
    if _command_regex.match(text):
        return text
    return None


def current_full_path() -> list[str]:
    """
    XSH path might contain additional items (e.g. npm). So merge.
    """
    xsh_path: list[str] = []
    if XSH.env:
        xsh_path = cast(list[str], XSH.env.get("PATH"))
    env_path = os.environ.get("PATH", "").split(os.pathsep)
    if sys.platform.startswith("win"):
        env_path.insert(0, os.curdir)  # implied by Windows shell
    return xsh_path + [p for p in env_path if p not in xsh_path]


@Condition
def whitespace_only() -> bool:
    app = get_app()
    buf = app.current_buffer
    return not buf.text.strip()


@Condition
def is_typo_command() -> bool:
    """
    Is the command itself invalid? Should be conservative, so we can suppress
    executing it if it is definitely a typo.
    """

    app = get_app()
    buf = app.current_buffer
    text = buf.text.strip()

    is_default_buffer = buf.name == "DEFAULT_BUFFER"
    if not is_default_buffer:
        return False

    # Assistant NL requests always allowed.
    has_assistant_prefix = text.startswith("?") or text.rstrip().endswith("?")
    if has_assistant_prefix:
        return False

    # Anything more complex is probably Python.
    # TODO: Do a better syntax parse of this as Python, or use xonsh's algorithm.
    for s in ["\n", "(", ")"]:
        if s in text:
            return False

    # Empty command line allowed.
    if not text:
        return False

    # Now look at the command.
    command_name = _extract_command_name(text)

    # Python or missing command is fine.
    if not command_name:
        return False

    # Recognized command.
    if is_valid_command(command_name, current_full_path()):
        return False

    # Okay it's almost certainly a command typo.
    return True


@Condition
def is_completion_menu_active() -> bool:
    app = get_app()
    return app.current_buffer.complete_state is not None


def add_key_bindings() -> None:
    custom_bindings = KeyBindings()

    @custom_bindings.add(" ", filter=whitespace_only)
    def _(event: KeyPressEvent):
        """
        Map space at the start of the line to `? ` to invoke an assistant question.
        """
        buf = event.app.current_buffer
        if buf.text == " " or buf.text == "":
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text("? ")
        else:
            buf.insert_text(" ")

    @custom_bindings.add(" ", filter=is_typo_command)
    def _(event: KeyPressEvent):
        """
        If the user types two words and the first word is likely an invalid
        command, prefix with `? `.
        """

        buf = event.app.current_buffer
        text = buf.text.strip()

        if len(text.split()) >= 2 and not text.startswith("?"):
            buf.transform_current_line(lambda line: "? " + line)
            buf.cursor_position += 2

        buf.insert_text(" ")

    @custom_bindings.add("enter", filter=is_unquoted_assist_request)
    def _(event: KeyPressEvent):
        """
        Automatically add quotes around assistant questions, so there are not
        syntax errors if the command line contains unclosed quotes etc.
        """

        buf = event.app.current_buffer
        text = buf.text.strip()

        question_text = text[1:].strip()
        if not question_text:
            # If the user enters an empty assistant request, treat it as a shortcut to go to the assistant chat.
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text(assistant_chat.name)
        else:
            # Convert it to an assistant question starting with a `?`.
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text(assist_request_str(question_text))

        buf.validate_and_handle()

    @custom_bindings.add("enter", filter=is_typo_command)
    def _(event: KeyPressEvent):
        """
        Suppress enter and if possible give completions if the command is just not a valid command.
        """

        buf = event.app.current_buffer
        buf.start_completion()

    # TODO: Also suppress enter if a command or action doesn't meet the required args,
    # selection, or preconditions.
    # Perhaps also have a way to get confirmation if its a rarely used or unexpected command
    # (based on history/suggestions).
    # TODO: Add suggested replacements, e.g. df -> duf, top -> btm, etc.

    @custom_bindings.add("@")
    def _(event: KeyPressEvent):
        """
        Auto-trigger item completions after `@` sign.
        """
        buf = event.app.current_buffer
        buf.insert_text("@")
        buf.start_completion()

    @custom_bindings.add("escape", eager=True, filter=is_completion_menu_active)
    def _(event: KeyPressEvent):
        """
        Close the completion menu when escape is pressed.
        """
        event.app.current_buffer.cancel_completion()

    @custom_bindings.add("tab")
    def _(event: KeyPressEvent):
        """
        Bind tab since sometimes it's not called e.g. after space then tab.
        """
        buf = event.app.current_buffer
        buf.start_completion()

    existing_bindings = __xonsh__.shell.shell.prompter.app.key_bindings  # type: ignore  # noqa: F821
    merged_bindings = merge_key_bindings([existing_bindings, custom_bindings])
    __xonsh__.shell.shell.prompter.app.key_bindings = merged_bindings  # type: ignore  # noqa: F821

    log.info("Added custom %s key bindings.", len(merged_bindings.bindings))


def load_completers():
    add_one_completer("command_or_action_completer", command_or_action_completer, "start")
    add_one_completer("item_completer", item_completer, "start")
    add_one_completer("at_prefix_completer", at_prefix_completer, "start")
    add_one_completer("help_question_completer", help_question_completer, "start")
    add_one_completer("options_completer", options_completer, "start")
