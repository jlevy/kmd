from kmd.commands.command_results import CommandResult
from kmd.config.logger import NONFATAL_EXCEPTIONS, get_console, get_logger
from kmd.config.text_styles import (
    COLOR_ERROR,
    SPINNER,
)
from kmd.exec.action_exec import run_action
from kmd.file_storage.workspaces import current_workspace
from kmd.help.command_help import output_command_help
from kmd.model.actions_model import Action
from kmd.model.params_model import RUNTIME_ACTION_PARAMS
from kmd.shell_tools.exception_printing import summarize_traceback
from kmd.shell_tools.option_parsing import parse_shell_args
from kmd.text_ui.command_output import output
from kmd.util.log_calls import log_tallies

log = get_logger(__name__)


class ShellCallableAction:
    def __init__(self, action: Action):
        self.action = action
        self.__name__ = action.name
        self.__doc__ = action.description

    def __call__(self, args) -> CommandResult:
        shell_args = parse_shell_args(args)

        if shell_args.show_help:
            param_docs = self.action.params() + list(RUNTIME_ACTION_PARAMS.values())

            output_command_help(
                self.action.name,
                self.action.description,
                param_docs=param_docs,
                precondition=self.action.precondition,
            )

            return CommandResult()

        # Handle --rerun option at action invocation time.
        rerun = bool(shell_args.kw_args.get("rerun", False))

        self.action = self.action.update_with_params(shell_args.kw_args, strict=True)

        try:
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    run_action(self.action, *shell_args.pos_args, rerun=rerun)
            else:
                run_action(self.action, *args, rerun=rerun)
            # We don't return the result to keep the xonsh shell output clean.
        except NONFATAL_EXCEPTIONS as e:
            output()
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
            return CommandResult(exception=e)
        finally:
            log_tallies(if_slower_than=10.0)

        return CommandResult(
            selection=current_workspace().get_selection(),
            show_selection=True,
            suggest_actions=True,
        )

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
