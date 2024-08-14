from typing import Callable, List, Optional, TypeVar
from kmd.config.logger import NONFATAL_EXCEPTIONS, get_console, get_logger
from kmd.config.text_styles import (
    COLOR_ERROR,
    SPINNER,
)
from kmd.text_ui.command_output import output
from kmd.exec.action_exec import run_action
from kmd.commands import commands
from kmd.model.actions_model import Action
from kmd.util.log_calls import log_tallies


log = get_logger(__name__)


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
            and not line.lstrip().startswith("The above exception") and not line.startswith("    ")
        ]
        + ["Run `logs` for details."]
    )


R = TypeVar("R")


def wrap_with_exception_printing(func: Callable[..., R]) -> Callable[[List[str]], Optional[R]]:
    def command(*args) -> Optional[R]:
        try:
            return func(*args)
        except NONFATAL_EXCEPTIONS as e:
            log.error(f"[{COLOR_ERROR}]Command error:[/{COLOR_ERROR}] %s", _summarize_traceback(e))
            output()
            log.info("Command error details: %s", e, exc_info=True)

    command.__name__ = func.__name__
    command.__doc__ = func.__doc__
    return command


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
            log.error(f"[{COLOR_ERROR}]Action error:[/{COLOR_ERROR}] %s", _summarize_traceback(e))
            log.info("Action error details: %s", e, exc_info=True)
        finally:
            log_tallies(if_slower_than=10.0)
            # Show the current selection.
            commands.select()

    def __repr__(self):
        return f"CallableAction({str(self.action)})"
