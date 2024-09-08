from dataclasses import dataclass
import threading
from typing import List
from kmd.config.text_styles import EMOJI_TASK, EMOJI_TASK_SEP


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
        unit_prefix = ""
        parts_str = ""
        if self.unit:
            unit_prefix = f"{self.unit} "
        if self.total_parts > 1:
            parts_str = f" ({unit_prefix}{self.current_part}/{self.total_parts})"
        return f"{self.name}{parts_str}"

    def err_str(self):
        return f"({self.errors} {'errs' if self.errors > 1 else 'err'})" if self.errors else ""

    def full_str(self):
        return f"{self.task_str()}{self.err_str()}"

    def prefix_str(self):
        return EMOJI_TASK_SEP

    def __str__(self) -> str:
        return f"TaskState({self.full_str()})"


def log_task_stack(task_str: str):
    from kmd.config.logger import get_logger
    from kmd.text_ui.command_output import output

    log = get_logger(__name__)
    output()
    log.message("%s %s:", EMOJI_TASK, task_str)


class TaskStack:
    """
    A TaskStack is the state, typically stored in a thread-local variable, for a sequence of tasks
    that may be recursive, each with one or more parts. New task states can be pushed and popped.
    """

    def __init__(self):
        self.stack: List[TaskState] = []

    def push(self, name: str, total_parts: int = 1, unit: str = ""):
        self.stack.append(TaskState(name, 0, total_parts, unit))
        if self.current_task.total_parts == 1:
            log_task_stack(self.full_str())

    def pop(self) -> TaskState:
        if not self.stack:
            raise IndexError("Pop from empty task stack")
        return self.stack.pop()

    def next_part(self, last_had_error: bool = False):
        self.current_task.next()
        if last_had_error:
            self.current_task.errors += 1

        log_task_stack(self.full_str())

    @property
    def current_task(self) -> TaskState:
        if not self.stack:
            raise IndexError("No current task stack")
        return self.stack[-1]

    def full_str(self) -> str:
        if not self.stack:
            return ""
        else:
            return " > ".join(state.full_str() for state in self.stack)

    def prefix_str(self) -> str:
        if not self.stack:
            return ""
        else:
            return "".join(state.prefix_str() for state in self.stack)

    def __str__(self):
        return f"TaskStack({self.full_str()})"


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
