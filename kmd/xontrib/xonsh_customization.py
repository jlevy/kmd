import threading
import time
from types import NoneType
from typing import Any, Callable, Dict, List, TypeVar
from xonsh.completers.completer import add_one_completer
from kmd.commands.command_registry import all_commands
from kmd.commands.command_results import print_command_result_info
from kmd.config.setup import setup
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    PROMPT_COLOR_NORMAL,
    PROMPT_COLOR_WARN,
    PROMPT_MAIN,
)
from kmd.shell_tools.action_wrapper import ShellCallableAction
from kmd.shell_tools.function_wrapper import wrap_for_shell_args
from kmd.text_ui.command_output import output
from kmd.file_storage.workspaces import current_workspace
from kmd.action_defs import reload_all_actions
from kmd.commands import commands
from kmd.commands.commands import CommandResult, welcome
from kmd.shell_tools.exception_printing import wrap_with_exception_printing
from kmd.version import get_version


setup()  # Call to config logging before anything else.

log = get_logger(__name__)


# Make type checker happy with xonsh globals:


def get_env(name: str) -> Any:
    return __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_env(name: str, value: Any) -> None:
    __xonsh__.env[name] = value  # type: ignore  # noqa: F821


def set_alias(name: str, value: str | Callable) -> None:
    aliases[name] = value  # type: ignore  # noqa: F821


def update_aliases(new_aliases: Dict[str, str | Callable]) -> None:
    aliases.update(new_aliases)  # type: ignore  # noqa: F821


_is_interactive = get_env("XONSH_INTERACTIVE")


R = TypeVar("R")


def _wrap_handle_results(func: Callable[..., R]) -> Callable[[List[str]], NoneType]:

    def command(*args) -> None:
        retval = func(*args)

        res: CommandResult
        if isinstance(retval, CommandResult):
            res = retval
        else:
            res = CommandResult(retval)

        set_env("result", res.result)
        set_env("selection", res.selection)

        print_command_result_info(res)

        return None

    command.__name__ = func.__name__
    command.__doc__ = func.__doc__
    return command


def _load_xonsh_commands():
    """
    Load all kmd commands as xonsh commands.
    """
    kmd_commands = {}

    # kmd command aliases in xonsh.
    kmd_commands["kmd_help"] = commands.kmd_help

    # Override default ? command.
    kmd_commands["?"] = "assist"

    # TODO: Figure out how to get this to work:
    # _set_alias("py_help", help)
    # _set_alias("help", commands.kmd_help)

    # TODO: Doesn't seem to reload modified Python?
    # def reload() -> None:
    #     xontribs.xontribs_reload(["kmd"], verbose=True)
    #
    # _set_alias("reload", reload)

    global _commands
    _commands = all_commands()

    for func in _commands.values():
        kmd_commands[func.__name__] = _wrap_handle_results(
            wrap_with_exception_printing(wrap_for_shell_args(func))
        )

    update_aliases(kmd_commands)


def _load_xonsh_actions():
    """
    Load all kmd actions as xonsh commands.
    """
    kmd_actions = {}
    global _actions
    _actions = reload_all_actions()

    for action in _actions.values():
        kmd_actions[action.name] = _wrap_handle_results(ShellCallableAction(action))

    update_aliases(kmd_actions)


def _load_completers():
    from kmd.xontrib.xonsh_completers import (
        command_or_action_completer,
        item_completer,
        help_question_completer,
        options_completer,
    )

    add_one_completer("command_or_action_completer", command_or_action_completer, "start")
    add_one_completer("item_completer", item_completer, "start")
    add_one_completer("help_question_completer", help_question_completer, "start")
    add_one_completer("options_completer", options_completer, "start")


def _initialize():
    if _is_interactive:
        # Try to seem a little faster starting up.
        def load():
            load_start_time = time.time()

            _load_xonsh_commands()
            _load_xonsh_actions()

            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")

            # These depend on commands and actions being loaded.
            _load_completers()

        load_thread = threading.Thread(target=load)
        load_thread.start()

        output()
    else:
        _load_xonsh_commands()
        _load_xonsh_actions()


def _post_initialize():
    if _is_interactive:
        current_workspace()  # Validates and logs info for user.
        output()


def _kmd_xonsh_prompt():
    from kmd.file_storage.workspaces import current_workspace_info

    path, is_sandbox = current_workspace_info()
    name = path.name if path else None
    workspace_str = (
        f"{{{PROMPT_COLOR_NORMAL}}}" + name
        if name and not is_sandbox
        else f"{{{PROMPT_COLOR_WARN}}}(sandbox)"
    )
    return f"{workspace_str} {{{PROMPT_COLOR_NORMAL}}}{PROMPT_MAIN}{{RESET}} "


def _shell_setup():
    set_env("PROMPT", _kmd_xonsh_prompt)


def customize_xonsh():
    """
    Everything to customize xonsh for kmd.
    """

    if _is_interactive:
        welcome()  # Do first since init could take a few seconds.

    _initialize()

    _post_initialize()

    _shell_setup()

    log.info("kmd %s loaded", get_version())