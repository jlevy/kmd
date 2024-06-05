import functools
import time
from typing import Any, Callable
import regex
from strif import abbreviate_str
from kmd.config.logger import get_logger
from kmd.config.text_styles import EMOJI_TIME

log = get_logger(__name__)


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


DEFAULT_TRUNCATE = 36


def abbreviate_arg(
    value: Any, repr_func: Callable = repr, truncate_length: int = DEFAULT_TRUNCATE
) -> str:
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
    if seconds < 100.0 / 1000.0:
        return f"{seconds * 1000:.3f}ms"
    elif seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 100.0:
        return f"{seconds:.3f}s"
    else:
        return f"{seconds:.1f}s"


def log_calls(
    level: str = "info",
    show_args=True,
    show_return=False,
    if_slower_than: float = 0.0,
    truncate_length: int = DEFAULT_TRUNCATE,
    repr_func: Callable = repr,
):
    """
    Decorator to log function calls and returns and time taken, with optional display of
    arguments and return values. If `if_slower_than_sec` is set, only log calls that take longer
    than that number of seconds.
    """
    to_str = lambda value: abbreviate_arg(value, repr_func, truncate_length)

    def format_args(args, kwargs):
        return ", ".join(
            [to_str(arg) for arg in args] + [f"{k}={to_str(v)}" for k, v in kwargs.items()]
        )

    def format_call(func, args, kwargs):
        if show_args:
            return f"{func.__name__}({format_args(args, kwargs)})"
        else:
            return func.__name__

    log_func = getattr(log, level.lower())

    show_call = True
    if if_slower_than > 0.0:
        show_call = False

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if show_call:
                log_func(f"≫ Call: {format_call(func, args, kwargs)}")

            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed = end_time - start_time

            if show_call:
                call_msg = f"≪ Call done: {func.__name__} in {format_duration(elapsed)}"
                if show_return:
                    log_func("%s: %s", call_msg, to_str(result))
                else:
                    log_func("%s", call_msg)
            else:
                if elapsed > if_slower_than:
                    call_msg = (
                        f"{EMOJI_TIME} Call to {func.__name__} took {format_duration(elapsed)}."
                    )
                    log_func("%s", call_msg)

            return result

        return wrapper

    return decorator
