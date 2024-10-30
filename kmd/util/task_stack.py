import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import List

from kmd.config.text_styles import (
    EMOJI_BREADCRUMB_SEP,
    EMOJI_MSG_INDENT,
    EMOJI_TASK,
    TASK_STACK_HEADER,
)


@dataclass
class TaskState:
    name: str
    current_part: int
    total_parts: int
    unit: str = ""
    errors: int = 0

    def next(self):
        self.current_part += 1

    def task_str(self):
        done_str = "(done)" if self.current_part == self.total_parts else None
        unit_str = None
        parts_str = None
        if self.current_part < self.total_parts:
            unit_str = self.unit or None
            parts_str = f"{min(self.current_part + 1, self.total_parts)}/{self.total_parts}"

        parenthetical = None
        if unit_str or parts_str:
            parenthetical = (
                f"({unit_str} {parts_str})"
                if unit_str and parts_str
                else f"({unit_str or parts_str})"
            )

        pieces = [self.name, done_str, parenthetical]
        return " ".join(filter(bool, pieces))

    def err_str(self):
        return f" [{self.errors} {'errs' if self.errors > 1 else 'err'}!]" if self.errors else ""

    def full_str(self):
        return f"{self.task_str()}{self.err_str()}"

    def prefix_str(self):
        return EMOJI_MSG_INDENT

    def __str__(self) -> str:
        return f"TaskState({self.full_str()})"


class TaskStack:
    """
    A TaskStack is the state, typically stored in a thread-local variable, for a sequence of tasks
    that may be recursive, each with one or more parts. New task states can be pushed and popped.
    This is useful for logging progress, task depth, etc.
    """

    def __init__(self):
        self.stack: List[TaskState] = []

    def push(self, name: str, total_parts: int = 1, unit: str = ""):
        self.stack.append(TaskState(name, 0, total_parts, unit))
        self.log()

    def pop(self) -> TaskState:
        if not self.stack:
            raise IndexError("Pop from empty task stack")
        return self.stack.pop()

    def next(self, last_had_error: bool = False):
        """
        Call after of each part of a task.
        """
        self.current_task.next()
        if last_had_error:
            self.current_task.errors += 1

        self.log()

    @property
    def current_task(self) -> TaskState:
        if not self.stack:
            raise IndexError("No current task stack")
        return self.stack[-1]

    def full_str(self) -> str:
        if not self.stack:
            return ""
        else:
            prefix = f"{EMOJI_TASK} "
            sep = f" {EMOJI_BREADCRUMB_SEP}\n{EMOJI_TASK} "
            return prefix + sep.join(state.full_str() for state in self.stack)

    def prefix_str(self) -> str:
        if not self.stack:
            return ""
        else:
            return "".join(state.prefix_str() for state in self.stack)

    def __str__(self):
        return f"TaskStack({self.full_str()})"

    def log(self):
        self._output()
        self._log.message(f"{TASK_STACK_HEADER}\n%s", self.full_str())

    @contextmanager
    def context(self, name: str, total_parts: int = 1, unit: str = ""):
        self.push(name, total_parts, unit)
        try:
            yield self
        except Exception as e:
            self._log.warning("Exception in task context: %s: %s", type(e).__name__, e)
            self.next(last_had_error=True)
            raise
        finally:
            self.pop()

    # Lazy importing to minimize circular imports.
    @property
    def _log(self):
        from kmd.config.logger import get_logger

        return get_logger(__name__)

    @property
    def _output(self):
        from kmd.shell.shell_output import cprint

        return cprint


_thread_local = threading.local()


def task_stack() -> TaskStack:
    if not hasattr(_thread_local, "task_stack"):
        _thread_local.task_stack = TaskStack()

    return _thread_local.task_stack


def task_stack_prefix_str() -> str:
    if hasattr(_thread_local, "task_stack"):
        task_stack: TaskStack = _thread_local.task_stack
        return task_stack.prefix_str()
    else:
        return ""
