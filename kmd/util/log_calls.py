import functools
import time
from typing import Any, Callable
import regex
from strif import abbreviate_str
from kmd.config.logger import get_logger

log = get_logger(__name__)


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


def abbreviate_arg(value: Any, repr_func: Callable = repr, truncate_length: int = 32) -> str:
    """
    Abbreviate an argument value for logging.
    """
    if isinstance(value, str) and truncate_length:
        result = repr_func(abbreviate_str(single_line(value), truncate_length, indicator="…"))
        if len(result) >= truncate_length:
            result += f" ({len(value)} chars)"
        return result
    elif truncate_length:
        return abbreviate_str(repr_func(value), truncate_length, indicator="…")
    else:
        return single_line(repr_func(value))


def format_duration(seconds: float) -> str:
    if seconds < 1.0:
        return f"{seconds * 1000:.3f}ms"
    else:
        return f"{seconds:.3f}s"


def log_calls(
    level: str = "info",
    show_args=True,
    show_return=False,
    truncate_length: int = 32,
    repr_func: Callable = repr,
):
    """
    Decorator to log function calls and returns and time taken, with optional display of
    arguments and return values.
    """
    to_str = lambda value: abbreviate_arg(value, repr_func, truncate_length)

    log_func = getattr(log, level.lower())

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if show_args:
                args_str = ", ".join(
                    [to_str(arg) for arg in args] + [f"{k}={to_str(v)}" for k, v in kwargs.items()]
                )
                log_func(f"≫ Call: {func.__name__}({args_str})")
            else:
                log_func(f"->Call: {func.__name__}")
            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed = end_time - start_time
            if show_return:
                log_func(f"≪ Done: {func.__name__} in {format_duration(elapsed)}: {to_str(result)}")
            else:
                log_func(f"≪ Done: {func.__name__} in {format_duration(elapsed)}")
            return result

        return wrapper

    return decorator
