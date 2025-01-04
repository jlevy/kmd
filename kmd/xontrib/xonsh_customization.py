import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, TypeVar

from xonsh.built_ins import XSH
from xonsh.prompt.base import PromptFields
from xonsh.xontribs import xontribs_load

from kmd.action_defs import reload_all_actions
from kmd.commands import help_commands
from kmd.commands.command_registry import all_commands
from kmd.config.logger import get_logger
from kmd.config.setup import print_api_key_setup, setup
from kmd.config.text_styles import PROMPT_COLOR_NORMAL, PROMPT_COLOR_WARN, PROMPT_MAIN
from kmd.exec.history import wrap_with_history
from kmd.model.actions_model import Action
from kmd.model.shell_model import ShellResult
from kmd.server.local_server import start_server
from kmd.server.local_url_formatters import enable_local_urls
from kmd.shell.shell_output import cprint
from kmd.shell.shell_results import handle_shell_result, shell_before_exec
from kmd.shell_tools.action_wrapper import ShellCallableAction
from kmd.shell_tools.exception_printing import wrap_with_exception_printing
from kmd.shell_tools.function_wrapper import wrap_for_shell_args
from kmd.shell_tools.native_tools import tool_check
from kmd.shell_tools.tool_deps import check_terminal_features, Tool
from kmd.version import get_version_name
from kmd.workspaces.workspaces import current_workspace
from kmd.xontrib.xonsh_completers import load_completers


setup()  # Call to config logging before anything else.

log = get_logger(__name__)


# Make type checker happy with xonsh globals:


def get_env(name: str) -> Any:
    return __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_env(name: str, value: Any) -> None:
    __xonsh__.env[name] = value  # type: ignore  # noqa: F821


def unset_env(name: str) -> None:
    del __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_alias(name: str, value: str | Callable) -> None:
    aliases[name] = value  # type: ignore  # noqa: F821


def update_aliases(new_aliases: Dict[str, str | Callable]) -> None:
    aliases.update(new_aliases)  # type: ignore  # noqa: F821


_is_interactive = get_env("XONSH_INTERACTIVE")


R = TypeVar("R")


def _wrap_handle_results(func: Callable[..., R]) -> Callable[[List[str]], None]:

    def command(args: List[str]) -> None:

        shell_before_exec()

        # Run the function.
        retval = func(args)

        res: ShellResult
        if isinstance(retval, ShellResult):
            res = retval
        else:
            res = ShellResult(retval)

        # Put result and selections in environment as $result, $selection, and $selections
        # for convenience for the user to access from the shell if needed.

        set_env("result", res.result)

        silent = not _is_interactive  # Don't log workspace info unless interactive.

        selections = current_workspace(silent=silent).selections
        selection = selections.current
        set_env("selections", selections)
        set_env("selection", selection)

        handle_shell_result(res)

        return None

    command.__name__ = func.__name__
    command.__doc__ = func.__doc__
    return command


_commands: Dict[str, Callable[..., Any]]

_actions: Dict[str, Action]


def _load_xonsh_commands():
    """
    Load all kmd commands as xonsh commands.
    """
    kmd_commands = {}

    # Override default ? command.
    kmd_commands["?"] = "assist"

    # Override the default Python help command.
    # builtin.help must not be loaded or this won't work.
    set_alias("help", help_commands.help)
    # An extra name just in case `help` doesn't work.
    set_alias("kmd_help", help_commands.help)
    # A backup for xonsh's built-in history command.
    set_alias("xhistory", aliases["history"])  # type: ignore  # noqa: F821

    # TODO: Doesn't seem to reload modified Python?
    # def reload() -> None:
    #     xontribs.xontribs_reload(["kmd"], verbose=True)
    #
    # _set_alias("reload", reload)

    global _commands
    _commands = all_commands()

    # TODO: Move history to include all shell commands?
    for func in _commands.values():
        kmd_commands[func.__name__] = _wrap_handle_results(
            wrap_with_exception_printing(wrap_for_shell_args(wrap_with_history(func)))
        )

    update_aliases(kmd_commands)


def _load_xonsh_actions() -> List[str]:
    """
    Load all kmd actions as xonsh commands.
    """
    kmd_actions = {}
    global _actions
    _actions = reload_all_actions()

    for action in _actions.values():
        kmd_actions[action.name] = _wrap_handle_results(ShellCallableAction(action))

    update_aliases(kmd_actions)

    return list(kmd_actions.keys())


def _initialize_commands():
    if _is_interactive:
        # Try to seem a little faster starting up.
        def load():
            load_start_time = time.time()

            _load_xonsh_commands()
            _load_xonsh_actions()

            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")

            # Completers depend on commands and actions being loaded.
            load_completers()

        load_thread = threading.Thread(target=load)
        load_thread.start()

        cprint()
    else:
        _load_xonsh_commands()
        _load_xonsh_actions()


# Xonsh default prompt for reference:
# dp = (
#     "{YELLOW}{env_name}{RESET}"
#     "{BOLD_GREEN}{user}@{hostname}{BOLD_BLUE} "
#     "{cwd}{branch_color}{curr_branch: {}}{RESET} "
#     "{RED}{last_return_code_if_nonzero:[{BOLD_INTENSE_RED}{}{RED}] }{RESET}"
#     "{BOLD_BLUE}{prompt_end}{RESET} "
# )


def _kmd_workspace_str():
    # Could do this faster with current_workspace_info() but actually it's nicer to load
    # and log info about the whole workspace after a cd so we do that.
    ws = current_workspace()
    ws_name = ws.name
    is_sandbox = ws.is_sandbox

    # Workspace name, different format if sandbox.
    if ws_name and not is_sandbox:
        workspace_str = ws_name
    else:
        workspace_str = "(sandbox)"

    # Add current directory to workspace name if necessary to clarify.
    cwd = Path(".").resolve()
    if cwd.is_relative_to(ws.base_dir):
        rel_cwd = cwd.relative_to(ws.base_dir)
        if rel_cwd != Path("."):
            workspace_str = f"{workspace_str}/{rel_cwd}"
    elif cwd.name != ws_name:
        workspace_str = f"{workspace_str} {cwd.name}"

    return workspace_str


def _kmd_xonsh_prompt():
    workspace_str = _kmd_workspace_str()
    # Apply colors to workspace string based on sandbox status
    ws = current_workspace()
    if ws.name and not ws.is_sandbox:
        colored_workspace_str = f"{{{PROMPT_COLOR_NORMAL}}}{workspace_str}"
    else:
        colored_workspace_str = f"{{{PROMPT_COLOR_WARN}}}{workspace_str}"

    colored_workspace_str = f"{colored_workspace_str}{{RESET}}"
    return f"\n{colored_workspace_str} {{{PROMPT_COLOR_NORMAL}}}{PROMPT_MAIN}{{RESET}} "


def _add_aliases() -> None:
    """
    Miscellaneous aliases to improve user experience, if they are installed.
    """
    installed_tools = tool_check()

    assert XSH.aliases
    if installed_tools.has(Tool.eza):
        XSH.aliases["ls"] = ["eza", "--group-directories-first"]
        XSH.aliases["ll"] = ["eza", "--group-directories-first", "-l"]
        XSH.aliases["lla"] = ["eza", "--group-directories-first", "-la"]


def _shell_setup():
    from kmd.xontrib.xonsh_completers import add_key_bindings

    # Set up a prompt field for the workspace string.
    fields = PromptFields(XSH)
    fields["workspace_str"] = _kmd_workspace_str
    set_env("PROMPT_FIELDS", fields)

    # Set up the prompt and title template.
    set_env("PROMPT", _kmd_xonsh_prompt)
    set_env("TITLE", "kmd - {workspace_str}")

    add_key_bindings()

    # Another convenience xontrib (fnm, since nvm doesn't work in xonsh).
    xontribs_load(["kmd.xontrib.fnm"], full_module=True)

    _add_aliases()


def customize_xonsh():
    """
    Everything to customize xonsh for kmd.
    """

    if _is_interactive:
        help_commands.welcome()  # Do first since init could take a few seconds.

    _initialize_commands()

    if _is_interactive:

        check_terminal_features().print_term_info()

        print_api_key_setup(once=False)

        if os.environ.get("TERM_PROGRAM") == "Kyrm":
            start_server()
            enable_local_urls(True)
        else:
            cprint(
                "If your terminal supports it, you may use `start_server` to enable local links."
            )

        current_workspace()  # Validates and logs info for user.
        cprint()

        _shell_setup()

        tool_check().warn_if_missing()

    log.info("kmd %s loaded", get_version_name())
