from functools import wraps
from pathlib import Path
from typing import Callable, List, Sequence, Tuple, TypeVar

from frontmatter_format import new_yaml, yaml_util
from pydantic import BaseModel, Field, field_serializer, field_validator, PrivateAttr

from kmd.config.logger import get_logger
from kmd.errors import InvalidOperation
from kmd.model.paths_model import fmt_loc, StorePath
from kmd.util.format_utils import fmt_count_items, fmt_lines

log = get_logger(__name__)

SH = TypeVar("SH", bound="SelectionHistory")
T = TypeVar("T")


def persist_after(save_method: Callable[[SH], None]):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self: SH, *args, **kwargs) -> T:
            result = func(self, *args, **kwargs)
            log.info("Saving selection history after %s().", func.__name__)
            save_method(self)
            return result

        return wrapper

    return decorator


class Selection(BaseModel):
    """
    A selection is a list of store paths for items in the workspace.
    """

    paths: List[StorePath] = Field(default_factory=list)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_serializer("paths")
    def serialize_paths(self, paths) -> List[str]:
        return [p.display_str() for p in paths]

    @field_validator("paths", mode="before")
    @classmethod
    def deserialize_paths(cls, paths: List[str]) -> List[StorePath]:
        return [StorePath(p) for p in paths]

    def remove_values(self, targets: Sequence[StorePath]) -> None:
        """
        Remove specified paths from the current selection.
        """
        self.paths = [p for p in self.paths if p not in targets]

    def replace_values(self, replacements: Sequence[Tuple[StorePath, StorePath]]) -> None:
        """
        Replace paths in the current selection according to the replacement pairs.
        """
        for old_path, new_path in replacements:
            for idx, current_path in enumerate(self.paths):
                if current_path == old_path:
                    self.paths[idx] = new_path

    def as_str(self, max_lines: int = 20) -> str:
        lines = [
            f"{fmt_count_items(len(self.paths), 'item')}:",
            fmt_lines(fmt_loc(s) for s in self.paths[:max_lines]),
        ]
        if len(self.paths) > max_lines:
            lines.append(f"\n… and {len(self.paths) - max_lines} more items")
        return "\n".join(lines)


class SelectionHistory(BaseModel):
    """
    A history stack of selections that can result from outputs of a sequence of commands.
    """

    history: List[Selection] = Field(default_factory=list)
    current_index: int = 0

    _save_path: Path = PrivateAttr()
    _max_history: int = PrivateAttr()

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @classmethod
    def init(cls, save_path: Path, max_history: int = 50) -> "SelectionHistory":
        """
        Initialize selection history, loading from save_path if it exists.
        """
        instance = cls()
        if save_path.exists():
            try:
                with save_path.open("r") as f:
                    data = new_yaml().load(f)
                instance = cls.model_validate(data)
            except Exception as e:
                log.warning(f"Error loading selection history, so will clear selections: {e}")

        instance._save_path = save_path
        instance._max_history = max_history
        return instance

    def save(self) -> None:
        """
        Save the current state.
        """
        data = self.model_dump()
        yaml_util.write_yaml_file(data, str(self._save_path))

    @persist_after(save)
    def clear(self) -> None:
        """
        Clear the history.
        """
        self.history.clear()
        self.current_index = 0

    def _clear_future(self) -> None:
        """
        Clear history beyond the current position.
        """
        del self.history[self.current_index + 1 :]

    def _truncate(self) -> None:
        """
        Truncate history to the given length.
        """
        if self._max_history > 0 and len(self.history) > self._max_history:
            prev_len = len(self.history)
            del self.history[: -self._max_history]
            self.current_index -= prev_len - len(self.history)

    @property
    def current(self) -> Selection:
        """
        Get the current selection, or an empty selection if there is no history.
        """
        if not self.history:
            return Selection(paths=[])
        else:
            return self.history[self.current_index]

    @persist_after(save)
    def set_current(self, store_paths: List[StorePath]) -> None:
        """
        Set the current selection. If history is empty, adds a new selection.
        """
        if not self.history:
            self.push(Selection(paths=store_paths))
        else:
            self.history[self.current_index] = Selection(paths=store_paths)

    @persist_after(save)
    def unselect_current(self, paths: Sequence[StorePath]) -> Selection:
        """
        Remove specified paths from the current selection.
        """
        if not self.history:
            raise InvalidOperation("No current selection")
        else:
            self.history[self.current_index].remove_values(paths)
            return self.history[self.current_index]

    @persist_after(save)
    def push(self, selection: Selection) -> None:
        """
        Append a new selection to history. If current_index is not at the end,
        discard the "future" history after the current position.
        """
        if not isinstance(selection, Selection):
            raise ValueError(f"Expected Selection, got {type(selection)}")

        self._clear_future()
        self.history.append(selection)
        self.current_index = len(self.history) - 1
        self._truncate()

    @persist_after(save)
    def pop(self) -> Selection:
        """
        Remove the current selection from history and return it.
        """
        if not self.history:
            raise InvalidOperation("No current selection")
        else:
            selection = self.history.pop()
            self.current_index = max(0, self.current_index - 1)
            return selection

    @persist_after(save)
    def previous(self) -> Selection:
        """
        Move to the previous selection in history and return it.
        """
        if self.current_index - 1 < 0:
            raise InvalidOperation("No previous selection")
        self.current_index -= 1
        return self.history[self.current_index]

    @persist_after(save)
    def next(self) -> Selection:
        """
        Move to the next selection in history and return it.
        """
        if self.current_index + 1 >= len(self.history):
            raise InvalidOperation("No next selection")
        self.current_index += 1
        return self.history[self.current_index]

    @persist_after(save)
    def remove_values(self, targets: Sequence[StorePath]) -> None:
        """
        Remove specified paths from all selections.
        """
        for selection in self.history:
            selection.remove_values(targets)

    @persist_after(save)
    def replace_values(self, replacements: Sequence[Tuple[StorePath, StorePath]]) -> None:
        """
        Replace paths in all selections according to the replacement pairs.
        """
        for selection in self.history:
            selection.replace_values(replacements)
