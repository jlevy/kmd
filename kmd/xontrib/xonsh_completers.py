import math
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import cast, Iterable, List, Tuple, TypeVar

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings

from thefuzz import fuzz
from xonsh.completers.completer import add_one_completer, RichCompletion
from xonsh.completers.tools import (
    CompleterResult,
    CompletionContext,
    contextual_completer,
    non_exclusive_completer,
)

from kmd.commands.help_commands import HELP_COMMANDS
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_ACTION_TEXT, COLOR_COMMAND_TEXT, EMOJI_TASK
from kmd.docs.faq_headings import faq_headings
from kmd.errors import InvalidState
from kmd.exec.system_actions import assistant_chat
from kmd.help.function_param_info import annotate_param_info
from kmd.model.items_model import Item
from kmd.model.params_model import Param
from kmd.model.paths_model import fmt_store_path
from kmd.model.preconditions_model import Precondition
from kmd.preconditions.precondition_checks import items_matching_precondition
from kmd.shell.shell_syntax import assist_request_str
from kmd.util.format_utils import single_line
from kmd.util.log_calls import log_calls
from kmd.util.type_utils import not_none
from kmd.workspaces.workspaces import current_ignore, current_workspace

log = get_logger(__name__)

MAX_COMPLETIONS = 500

MAX_DIR_COMPLETIONS = 100

# We want to keep completion fast, so make it obvious when it's slow.
SLOW_COMPLETION = 0.15

T = TypeVar("T")


@dataclass(frozen=True)
class Score:
    exact_prefix: float
    full_path: float
    filename: float
    recency: float
    # Could do title score too.
    total: float = field(init=False)

    def _total_score(self) -> float:
        return max(
            self.exact_prefix, 0.4 * self.full_path + 0.3 * self.filename + 0.3 * self.recency
        )

    def __post_init__(self):
        object.__setattr__(self, "total", self._total_score())

    def __lt__(self, other: "Score") -> bool:
        return self.total < other.total


_punct_re = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    return _punct_re.sub(" ", text.lower()).strip()


def score_exact_prefix(prefix: str, text: str) -> float:
    is_match = text.startswith(prefix)
    is_long_enough = len(prefix) >= 2
    return 100 if is_match and is_long_enough else 50 if is_match else 0


def score_phrase(prefix: str, text: str) -> float:
    # Could experiment with this more but it's a rough attempt to balance
    # full matches and prefix matches.
    return (
        0.4 * fuzz.token_set_ratio(prefix, text)
        + 0.4 * fuzz.partial_ratio(prefix, text)
        + 0.2 * fuzz.token_sort_ratio(prefix, text)
    )


def score_path(prefix: str, path: Path) -> Score:
    path_str = normalize(str(path))
    name_str = normalize(path.name)

    return Score(
        exact_prefix=max(
            score_exact_prefix(prefix, path_str), score_exact_prefix(prefix, name_str)
        ),
        full_path=max(score_phrase(prefix, path_str), score_phrase(prefix, name_str)),
        filename=score_phrase(prefix, name_str),
        recency=0,
    )


ONE_HOUR = 3600
ONE_YEAR = 3600 * 24 * 365


def score_recency(
    age_in_seconds: float, min_age: float = ONE_HOUR, max_age: float = ONE_YEAR
) -> float:
    """
    Calculate a score (0-100) based on age of the file's last modification.
    Uses an exponential decay curve to give higher weights to more recent changes.
    """
    if age_in_seconds <= min_age:
        return 100.0
    if age_in_seconds >= max_age:
        return 0.0

    age_after_min = age_in_seconds - min_age
    time_range = max_age - min_age

    decay_constant = 5.0 / time_range

    return 100.0 * math.exp(-decay_constant * age_after_min)


def score_item(prefix: str, item: Item) -> Score:
    path_score = score_path(prefix, Path(not_none(item.store_path)))

    timestamp = item.modified_at or item.created_at or None

    if not timestamp:
        return path_score
    else:
        age = (
            (datetime.now(timezone.utc) - item.modified_at).total_seconds()
            if item.modified_at
            else float("inf")
        )
        return replace(path_score, recency=score_recency(age))


def score_paths(prefix: str, paths: Iterable[Path]) -> List[Tuple[Score, Path]]:
    scored_paths = [(score_path(prefix, p), p) for p in paths]
    scored_paths.sort(key=lambda x: x[0], reverse=True)
    return scored_paths


def score_items(prefix: str, items: Iterable[Item]) -> List[Tuple[Score, Item]]:
    scored_items = [(score_item(prefix, item), item) for item in items]
    scored_items.sort(key=lambda x: x[0], reverse=True)
    return scored_items


def select_hits(
    scored_items: List[Tuple[Score, T]], min_score: float, max_hits: int
) -> List[Tuple[Score, T]]:
    """
    Filter scored items by minimum score and maximum count, preserving sort order.
    """
    return [(score, item) for score, item in scored_items[:max_hits] if score.total >= min_score]


def _dir_description(directory: Path) -> str:
    if not directory.exists():
        return ""
    # TODO: Cache, maybe also track size and other info.
    count = sum(1 for _ in directory.glob("*"))
    return f"{count} files"


def _all_help_completions(include_bare_qm: bool) -> List[RichCompletion]:
    questions = ["? " + question for question in faq_headings()]
    possible_completions = questions + HELP_COMMANDS
    if include_bare_qm:
        help_completion = RichCompletion("?", description="Ask a question to get help.")
        possible_completions.insert(0, help_completion)
    return [
        RichCompletion(question, display=question.lstrip("? ")) for question in possible_completions
    ]


def _command_match(query: str, values: Iterable[str | RichCompletion]) -> List[RichCompletion]:
    """
    Tighter match for command completions.
    """
    matches = []

    for value in values:
        completion = value if isinstance(value, RichCompletion) else RichCompletion(value)
        normalized_value = normalize(str(completion.value))

        if normalized_value.startswith(query) or score_phrase(query, normalized_value) > 90:
            matches.append(completion)

    return matches


@log_calls(level="debug")
def _command_completions(prefix: str) -> set[RichCompletion]:
    from kmd.xontrib.xonsh_customization import _actions, _commands

    prefix = normalize(prefix)

    command_matches = _command_match(prefix, [c.__name__ for c in _commands.values()])
    command_completions = [
        RichCompletion(
            name,
            description=single_line(_commands[name].__doc__ or ""),
            style=COLOR_COMMAND_TEXT,
        )
        for name in command_matches
    ]

    action_matches = _command_match(prefix, [a.name for a in _actions.values()])
    action_completions = [
        RichCompletion(
            name,
            display=f"{name} {EMOJI_TASK}",
            description=single_line(_actions[name].description or ""),
            style=COLOR_ACTION_TEXT,
            append_space=True,
        )
        for name in action_matches
    ]

    input_empty = not prefix.strip()
    help_completions = _command_match(prefix, _all_help_completions(input_empty))

    all_completions = command_completions + action_completions + help_completions
    all_completions.sort(key=completion_sort)

    return set(all_completions)


@log_calls(level="debug")
def _dir_completions(prefix: str, base_dir: Path) -> List[RichCompletion]:
    prefix = normalize(prefix)

    is_ignored = current_ignore()
    dirs = (d.relative_to(base_dir) for d in base_dir.iterdir() if d.is_dir() and not is_ignored(d))
    scored_paths = score_paths(prefix, dirs)

    hits = select_hits(scored_paths, min_score=60, max_hits=MAX_DIR_COMPLETIONS)

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

    hits = select_hits(scored_items, min_score=0, max_hits=MAX_COMPLETIONS)

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
        return cast(CompleterResult, _command_completions(prefix))

    return None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """
    from kmd.xontrib.xonsh_customization import _actions

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
        command = context.command
        arg_index = context.command.arg_index
        prefix = context.command.prefix.lstrip()

        # ?some question
        # ? some question
        if (arg_index == 0 and prefix.startswith("?")) or (
            arg_index == 1 and command.args[0].value == "?"
        ):
            query = prefix.lstrip("? ")
            return set(_command_match(query, _all_help_completions(False)))
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
    from kmd.xontrib.xonsh_customization import _actions, _commands

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


def add_key_bindings() -> None:
    custom_bindings = KeyBindings()

    @custom_bindings.add(" ")
    def _(event):
        """
        Map two spaces to `? ` to invoke an assistant question.
        """
        buf = event.app.current_buffer
        if buf.text == " ":
            buf.delete_before_cursor(2)
            buf.insert_text("? ")
        else:
            buf.insert_text(" ")

    @Condition
    def is_unquoted_assitant_request():
        app = get_app()
        buf = app.current_buffer
        text = buf.text.strip()
        return (
            buf.name == "DEFAULT_BUFFER"
            and text.startswith("?")
            and not (text.startswith('? "') or text.startswith("? '"))
        )

    @custom_bindings.add("enter", filter=is_unquoted_assitant_request)
    def _(event):
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
            # Wrap everything after '?' in quotes, preserving existing whitespace
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text(assist_request_str(question_text))

        buf.validate_and_handle()

    @custom_bindings.add("@")
    def _(event):
        """
        Auto-trigger item completions after `@` sign.
        """
        buf = event.app.current_buffer
        buf.insert_text("@")
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
