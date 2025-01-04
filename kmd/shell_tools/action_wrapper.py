from typing import List

from kmd.config.logger import get_console, get_logger
from kmd.config.text_styles import COLOR_ERROR, SPINNER

from kmd.errors import NONFATAL_EXCEPTIONS
from kmd.exec.action_exec import run_action
from kmd.exec.history import record_command
from kmd.help.command_help import print_action_help
from kmd.model.actions_model import Action
from kmd.model.commands_model import Command
from kmd.model.params_model import ParamValues
from kmd.model.shell_model import ShellResult
from kmd.shell_tools.exception_printing import summarize_traceback
from kmd.shell_ui.shell_output import cprint
from kmd.util.log_calls import log_tallies
from kmd.util.parse_shell_args import parse_shell_args

log = get_logger(__name__)


class ShellCallableAction:
    def __init__(self, action: Action):
        self.action = action
        self.__name__ = action.name
        self.__doc__ = action.description

    def __call__(self, args: List[str]) -> ShellResult:
        from kmd.shell_ui.shell_results import shell_before_exec

        shell_args = parse_shell_args(args)

        if shell_args.show_help:
            print_action_help(self.action, verbose=True)

            return ShellResult()

        # Handle --rerun option at action invocation time.
        rerun = bool(shell_args.options.get("rerun", False))

        log.info("Action shell args: %s", shell_args)

        # Command-line args overwrite any default values.
        self.action = self.action.with_param_values(
            ParamValues(shell_args.options), strict=True, overwrite=True
        )

        try:
            shell_before_exec()
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    result = run_action(self.action, *shell_args.args, rerun=rerun)
            else:
                result = run_action(self.action, *args, rerun=rerun)
            # We don't return the result to keep the xonsh shell output clean.
        except NONFATAL_EXCEPTIONS as e:
            cprint()
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
            return ShellResult(exception=e)
        finally:
            log_tallies(if_slower_than=10.0)
            # output_separator()

        # The handling of the output can be overridden by the action, but by default just show
        # the selection and suggested actions.
        if result.shell_result:
            shell_result = result.shell_result
        else:
            shell_result = ShellResult(
                show_selection=True,
                suggest_actions=True,
            )

        record_command(Command.assemble(self.action, args))

        return shell_result

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
