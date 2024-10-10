from typing import List

from kmd.config.logger import get_console, get_logger
from kmd.config.text_styles import COLOR_ERROR, SPINNER

from kmd.errors import NONFATAL_EXCEPTIONS
from kmd.exec.action_exec import run_action
from kmd.exec.history import record_command
from kmd.file_storage.workspaces import current_workspace
from kmd.help.command_help import output_action_help
from kmd.model.actions_model import Action
from kmd.model.commands_model import Command
from kmd.model.output_model import CommandOutput
from kmd.model.params_model import ParamSettings
from kmd.shell_tools.exception_printing import summarize_traceback
from kmd.text_ui.command_output import output
from kmd.util.log_calls import log_tallies
from kmd.util.parse_shell_args import parse_shell_args

log = get_logger(__name__)


class ShellCallableAction:
    def __init__(self, action: Action):
        self.action = action
        self.__name__ = action.name
        self.__doc__ = action.description

    def __call__(self, args: List[str]) -> CommandOutput:
        shell_args = parse_shell_args(args)

        if shell_args.show_help:
            output_action_help(self.action, verbose=True)

            return CommandOutput()

        # Handle --rerun option at action invocation time.
        rerun = bool(shell_args.kw_args.get("rerun", False))

        log.info("Action shell args: %s", shell_args)

        # Command-line args overwrite any default values.
        self.action = self.action.with_params(
            ParamSettings(shell_args.kw_args), strict=True, overwrite=True
        )

        try:
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    result = run_action(self.action, *shell_args.pos_args, rerun=rerun)
            else:
                result = run_action(self.action, *args, rerun=rerun)
            # We don't return the result to keep the xonsh shell output clean.
        except NONFATAL_EXCEPTIONS as e:
            output()
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
            return CommandOutput(exception=e)
        finally:
            log_tallies(if_slower_than=10.0)
            # output_separator()

        # The handling of the output can be overridden by the action, but by default just show
        # the selection and suggested actions.
        if result.command_output:
            command_output = result.command_output
        else:
            command_output = CommandOutput(
                selection=current_workspace().get_selection(),
                show_selection=True,
                suggest_actions=True,
            )

        record_command(Command.from_obj(self.action, args))

        return command_output

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
