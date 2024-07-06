from dataclasses import dataclass
import functools
import time
from typing import Any, Callable, Dict, Optional
import regex
from strif import abbreviate_str
from kmd.config.logger import get_logger
from kmd.text_ui.text_styles import EMOJI_CALL_BEGIN, EMOJI_CALL_END, EMOJI_TIMING

log = get_logger(__name__)


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


DEFAULT_TRUNCATE = 100


def abbreviate_arg(
    value: Any, repr_func: Callable = repr, truncate_length: Optional[int] = DEFAULT_TRUNCATE
) -> str:
    """
    Abbreviate an argument value for logging.
    """
    truncate_length = truncate_length or 0
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
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 100.0:
        return f"{seconds:.2f}s"
    else:
        return f"{seconds:.0f}s"


def func_and_module_name(func: Callable):
    short_module = func.__module__.split(".")[-1] if func.__module__ else None
    return f"{short_module}.{func.__qualname__}" if short_module else func.__qualname__


def log_calls(
    level: str = "info",
    show_args=True,
    show_return=False,
    if_slower_than: float = 0.0,
    truncate_length: Optional[int] = DEFAULT_TRUNCATE,
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

    def format_call(func_name: str, args, kwargs):
        if show_args:
            return f"{func_name}({format_args(args, kwargs)})"
        else:
            return func_name

    log_func = getattr(log, level.lower())

    show_call = True
    if if_slower_than > 0.0:
        show_call = False

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func_and_module_name(func)

            if show_call:
                log_func(f"{EMOJI_CALL_BEGIN} Call: {format_call(func_name, args, kwargs)}")

            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed = end_time - start_time

            if show_call:
                call_msg = f"{EMOJI_CALL_END} Call done: {func_name} in {format_duration(elapsed)}"
                if show_return:
                    log_func("%s: %s", call_msg, to_str(result))
                else:
                    log_func("%s", call_msg)
            else:
                if elapsed > if_slower_than:
                    call_msg = (
                        f"{EMOJI_TIMING} Call to {func_name} took {format_duration(elapsed)}."
                    )
                    log_func("%s", call_msg)

            return result

        return wrapper

    return decorator


@dataclass
class Tally:
    calls: int = 0
    total_time: float = 0.0
    last_logged_count: int = 0
    last_logged_total_time: float = 0.0


tally: Dict[str, Tally] = {}


def tally_calls(
    level: str = "info",
    min_total_runtime: float = 0.0,
    periodic_ratio: float = 2.0,
    if_slower_than: float = float("inf"),
):
    """
    Decorator to monitor performancy by tallying function calls and total runtime, only logging
    periodically (every time calls exceed `periodic_ratio` more in count or runtime than the last
    time it was logged) or if runtime is greater than `if_slower_than` seconds).
    """

    log_func = getattr(log, level.lower())

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed = end_time - start_time

            func_name = func_and_module_name(func)

            if func_name not in tally:
                tally[func_name] = Tally()

            tally[func_name].calls += 1
            tally[func_name].total_time += elapsed

            if tally[func_name].total_time >= min_total_runtime and (
                elapsed > if_slower_than
                or tally[func_name].calls >= periodic_ratio * tally[func_name].last_logged_count
                or tally[func_name].total_time
                >= periodic_ratio * tally[func_name].last_logged_total_time
            ):
                log_func(
                    "%s %s() took %s, now called %d times, %s avg per call, total time %s",
                    EMOJI_TIMING,
                    func_name,
                    format_duration(elapsed),
                    tally[func_name].calls,
                    format_duration(tally[func_name].total_time / tally[func_name].calls),
                    format_duration(tally[func_name].total_time),
                )
                tally[func_name].last_logged_count = tally[func_name].calls
                tally[func_name].last_logged_total_time = tally[func_name].total_time

            return result

        return wrapper

    return decorator


def log_tallies(if_slower_than: float = 0.0):
    """
    Log all tallies and runtimes of tallied functions.
    """
    tallies_to_log = {k: t for k, t in tally.items() if t.total_time >= if_slower_than}
    if tallies_to_log:
        log.message("%s Function tallies:", EMOJI_TIMING)
        for fkey, t in sorted(tally.items(), key=lambda item: item[1].total_time, reverse=True):
            log.message(
                "    %s() was called %d times, total time %s, avg per call %s",
                fkey,
                t.calls,
                format_duration(t.total_time),
                format_duration(t.total_time / t.calls) if t.calls else "N/A",
            )
