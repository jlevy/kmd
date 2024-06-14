"""
Xonsh extension for kmd.

Sets up all commands and functions for use in xonsh. This makes using kmd far easier
for interactive use than calling actions from a regular shell command line.
"""

import sys
from kmd.commands.command_output import output
from kmd.config.text_styles import COLOR_ERROR, COLOR_HEADING, COLOR_LOGO

# We want the kmd xontrib to always be loadable, but only activate if it's been invoked as kmdsh.
if sys.argv[0].endswith("/kmdsh"):
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from typing import Callable, List
    from rich import get_console
    from xonsh.tools import XonshError
    import litellm
    from kmd.config.setup import setup
    from kmd.config.settings import media_cache_dir
    from kmd.config.logger import get_logger
    from kmd.config.text_styles import EMOJI_WARN
    from kmd.file_storage.workspaces import current_workspace
    from kmd.action_exec.action_exec import run_action
    from kmd.action_exec.action_registry import load_all_actions
    from kmd.commands import commands
    from kmd.model.actions_model import Action
    from kmd.model.errors_model import SelfExplanatoryError, InvalidStoreState
    from kmd.util.log_calls import log_tallies

    setup()

    log = get_logger(__name__)

    # Common exceptions that don't merit a full stack trace.
    _common_exceptions = (SelfExplanatoryError, IOError, XonshError, litellm.exceptions.APIError)

    def _summarize_traceback(exception: Exception) -> str:
        exception_str = str(exception)
        lines = exception_str.splitlines()
        exc_type = type(exception).__name__
        return f"{exc_type}: " + "\n".join(
            [
                line
                for line in lines
                if line.strip() and not line.lstrip().startswith("Traceback")
                # and not line.lstrip().startswith("File ")
                and not line.lstrip().startswith("The above exception")
                and not line.startswith("    ")
            ]
            + ["Run `logs` for details."]
        )

    class CallableAction:
        def __init__(self, action: Action):
            self.action = action

        def __call__(self, args):
            try:
                with get_console().status(f"Running action {self.action.name}…", spinner="dots"):
                    run_action(self.action, *args)
                # We don't return the result to keep the xonsh shell output clean.
            except _common_exceptions as e:
                log.error(
                    f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", _summarize_traceback(e)
                )
                log.info("Action error details: %s", e, exc_info=True)
            finally:
                log_tallies(if_slower_than=10.0)
                output()

        def __repr__(self):
            return f"CallableAction({repr(self.action)})"

    def initialize():

        kmd_commands, kmd_actions = {}, {}

        # kmd command aliases.
        kmd_commands["kmd_help"] = commands.kmd_help

        # TODO: Figure out how to get this to work:
        # kmd_aliases["py_help"] = help
        # kmd_aliases["help"] = commands.kmd_help

        # TODO: Doesn't seem to reload modified Python?
        # def reload() -> None:
        #     xontribs.xontribs_reload(["kmd"], verbose=True)
        #
        # aliases["reload"] = reload  # type: ignore

        def xonsh_command_for(func: Callable):
            def command(args: List[str]):
                try:
                    func(*args)
                except _common_exceptions as e:
                    log.error(
                        f"[{COLOR_ERROR}]Command error:[/{COLOR_ERROR}] %s", _summarize_traceback(e)
                    )

                    log.info("Command error details: %s", e, exc_info=True)
                finally:
                    output()

            command.__doc__ = func.__doc__
            return command

        for func in commands.all_commands():
            kmd_commands[func.__name__] = xonsh_command_for(func)

        # Load all actions as xonsh commands.
        actions = load_all_actions()

        for action in actions.values():
            kmd_actions[action.name] = CallableAction(action)

        aliases.update(kmd_commands)  # type: ignore
        aliases.update(kmd_actions)  # type: ignore

        output()
        output("🄺", color=COLOR_LOGO)
        output()
        output("Welcome to kmd.\n", color=COLOR_HEADING)
        output()
        output(
            f"{len(kmd_commands)} commands and {len(kmd_actions)} actions are available.\n"
            "Use `kmd_help` for help.\n"
        )

        log.message(
            "Using media cache directory: %s\n",
            media_cache_dir(),
        )

    initialize()

    try:
        current_workspace()
    except InvalidStoreState as e:
        output(
            f"{EMOJI_WARN} The current directory is not a workspace. Create or switch to a workspace with the `workspace` command."
        )
    output()

    # TODO: Completion for actions, e.g. known URLs, resource titles, concepts, parameters and values, etc.
    # def _action_completer(cls, prefix, line, begidx, endidx, ctx):
    #     return ["https://"]
    # __xonsh__.completers["foo"] = _action_completer

    def _kmd_xonsh_prompt():
        from kmd.file_storage.workspaces import current_workspace_name

        name = current_workspace_name()
        workspace_str = "{BOLD_GREEN}" + name if name else "{INTENSE_YELLOW}(no workspace)"
        return "%s {BOLD_GREEN}❯{RESET} " % workspace_str

    __xonsh__.env["PROMPT"] = _kmd_xonsh_prompt  # type: ignore
