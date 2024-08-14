from kmd.config.logger import NONFATAL_EXCEPTIONS, get_console, get_logger
from kmd.config.text_styles import (
    COLOR_ERROR,
    SPINNER,
)
from kmd.exec.action_exec import run_action
from kmd.commands import commands
from kmd.model.actions_model import Action
from kmd.shell_tools.exception_printing import summarize_traceback
from kmd.util.log_calls import log_tallies

log = get_logger(__name__)


class ShellCallableAction:
    def __init__(self, action: Action):
        self.action = action

    def __call__(self, args):
        try:
            if not self.action.interactive_input:
                with get_console().status(f"Running action {self.action.name}…", spinner=SPINNER):
                    run_action(self.action, *args)
            else:
                run_action(self.action, *args)
            # We don't return the result to keep the xonsh shell output clean.
        except NONFATAL_EXCEPTIONS as e:
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
        finally:
            log_tallies(if_slower_than=10.0)

            # Show the current selection.
            commands.select()
            commands.applicable_actions(brief=True)

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
