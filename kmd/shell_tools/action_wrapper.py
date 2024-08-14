from typing import Dict, Iterable
from kmd.config.logger import NONFATAL_EXCEPTIONS, get_console, get_logger
from kmd.config.text_styles import (
    COLOR_ERROR,
    SPINNER,
)
from kmd.exec.action_exec import run_action
from kmd.commands import commands
from kmd.help.command_help import output_command_help
from kmd.model.actions_model import Action
from kmd.model.params_model import ALL_COMMON_PARAMS, Param
from kmd.shell_tools.exception_printing import summarize_traceback
from kmd.shell_tools.option_parsing import parse_shell_args
from kmd.util.log_calls import log_tallies

log = get_logger(__name__)


def _look_up_params(param_names: Iterable[str]) -> Dict[str, Param]:
    return {
        name: param
        for name, param in (
            (name, ALL_COMMON_PARAMS.get(name) or Param(name)) for name in param_names
        )
        if param is not None
    }


class ShellCallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        shell_args = parse_shell_args(args)

        if shell_args.show_help:
            param_info = _look_up_params(self.action.param_names())

            output_command_help(self.action.name, self.action.description, param_info)

            return

        self.action.update_with_params(shell_args.kw_args, strict=True)

        try:
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    run_action(self.action, *shell_args.pos_args)
            else:
                run_action(self.action, *args)
            # We don't return the result to keep the xonsh shell output clean.
        except NONFATAL_EXCEPTIONS as e:
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
            return
        finally:
            log_tallies(if_slower_than=10.0)

        # Show the current selection.
        commands.select()
        commands.applicable_actions(brief=True)

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
