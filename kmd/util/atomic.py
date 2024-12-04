import threading
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class AtomicVar(Generic[T]):
    """
    A simple thread-safe atomic variable. Simpler than other third-party libraries.
    """

    def __init__(self, initial_value: T = None):
        self._value: T = initial_value
        self.lock = threading.Lock()

    def get(self) -> T:
        with self.lock:
            return self._value

    def set(self, new_value: T) -> None:
        with self.lock:
            self._value = new_value

    def swap(self, new_value: T) -> T:
        """Set to new value and return the old value."""
        with self.lock:
            old_value = self._value
            self._value = new_value
            return old_value

    def update(self, fn: Callable[[T], T]) -> T:
        """Update value with a function and return the new value."""
        with self.lock:
            self._value = fn(self._value)
            return self._value

    def __bool__(self) -> bool:
        """Truthiness matches that of the underlying value."""
        return bool(self.get())

    def __str__(self) -> str:
        return str(self.get())
