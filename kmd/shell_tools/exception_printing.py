from typing import Callable, List, Optional, TypeVar
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    COLOR_ERROR,
)
from kmd.model.errors_model import NONFATAL_EXCEPTIONS
from kmd.text_ui.command_output import output


log = get_logger(__name__)


def summarize_traceback(exception: Exception) -> str:
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
        + ["\nRun `logs` for details."]
    )


R = TypeVar("R")


def wrap_with_exception_printing(func: Callable[..., R]) -> Callable[[List[str]], Optional[R]]:
    def command(*args) -> Optional[R]:
        try:
            log.info(
                "Wrapped function call: %s(%s)",
                func.__name__,
                (", ".join(str(arg) for arg in args)),
            )
            return func(*args)
        except NONFATAL_EXCEPTIONS as e:
            log.error(f"[{COLOR_ERROR}]Command error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            output()
            log.info("Command error details: %s", e, exc_info=True)

    command.__name__ = func.__name__
    command.__doc__ = func.__doc__
    return command
