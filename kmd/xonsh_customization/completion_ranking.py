import math
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, List, Tuple, TypeVar

from thefuzz import fuzz
from xonsh.completers.tools import RichCompletion

from kmd.config.logger import get_logger
from kmd.model.items_model import Item
from kmd.util.type_utils import not_none

log = get_logger(__name__)


T = TypeVar("T")


@dataclass(frozen=True)
class Score:
    exact_prefix: float
    full_path: float
    filename: float
    recency: float
    # Could do title score too.
    total: float = field(init=False)

    def _total_score(self) -> float:
        return max(
            self.exact_prefix, 0.4 * self.full_path + 0.3 * self.filename + 0.3 * self.recency
        )

    def __post_init__(self):
        object.__setattr__(self, "total", self._total_score())

    def __lt__(self, other: "Score") -> bool:
        return self.total < other.total


# xonsh's default Completer normalization.
# def normalize_xonsh(s: str) -> str:
#     s = str(s).lower().strip().lstrip("'\"")
#     if s.startswith("$"):
#         s = s[1:]
#     return s

_punct_re = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    return _punct_re.sub(" ", text.lower()).strip()


def score_exact_prefix(prefix: str, text: str) -> float:
    is_match = text.startswith(prefix)
    is_long_enough = len(prefix) >= 2
    return 100 if is_match and is_long_enough else 50 if is_match else 0


def score_phrase(prefix: str, text: str) -> float:
    # Could experiment with this more but it's a rough attempt to balance
    # full matches and prefix matches.
    return (
        0.4 * fuzz.token_set_ratio(prefix, text)
        + 0.4 * fuzz.partial_ratio(prefix, text)
        + 0.2 * fuzz.token_sort_ratio(prefix, text)
    )


def score_subphrase(prefix: str, text: str) -> float:
    return 0.5 * fuzz.partial_ratio(prefix, text) + 0.5 * fuzz.partial_token_set_ratio(prefix, text)


def score_path(prefix: str, path: Path) -> Score:
    path_str = normalize(str(path))
    name_str = normalize(path.name)

    return Score(
        exact_prefix=max(
            score_exact_prefix(prefix, path_str), score_exact_prefix(prefix, name_str)
        ),
        full_path=max(score_phrase(prefix, path_str), score_phrase(prefix, name_str)),
        filename=score_phrase(prefix, name_str),
        recency=0,
    )


ONE_HOUR = 3600
ONE_YEAR = 3600 * 24 * 365


def score_recency(
    age_in_seconds: float, min_age: float = ONE_HOUR, max_age: float = ONE_YEAR
) -> float:
    """
    Calculate a score (0-100) based on last use or modification time.
    Uses an exponential decay curve to give higher weights to more recent changes.
    """
    if age_in_seconds <= min_age:
        return 100.0
    if age_in_seconds >= max_age:
        return 0.0

    age_after_min = age_in_seconds - min_age
    time_range = max_age - min_age

    decay_constant = 5.0 / time_range

    return 100.0 * math.exp(-decay_constant * age_after_min)


def score_item(prefix: str, item: Item) -> Score:
    path_score = score_path(prefix, Path(not_none(item.store_path)))

    timestamp = item.modified_at or item.created_at or None

    if not timestamp:
        return path_score
    else:
        age = (
            (datetime.now(timezone.utc) - item.modified_at).total_seconds()
            if item.modified_at
            else float("inf")
        )
        return replace(path_score, recency=score_recency(age))


def score_paths(prefix: str, paths: Iterable[Path]) -> List[Tuple[Score, Path]]:
    scored_paths = [(score_path(prefix, p), p) for p in paths]
    scored_paths.sort(key=lambda x: x[0], reverse=True)
    return scored_paths


def score_items(prefix: str, items: Iterable[Item]) -> List[Tuple[Score, Item]]:
    scored_items = [(score_item(prefix, item), item) for item in items]
    scored_items.sort(key=lambda x: x[0], reverse=True)
    return scored_items


def select_hits_by_score(
    scored_items: List[Tuple[Score, T]], min_score: float, max_hits: int
) -> List[Tuple[Score, T]]:
    """
    Filter scored items by minimum score and maximum count, preserving sort order.
    """
    return [(score, item) for score, item in scored_items[:max_hits] if score.total >= min_score]


SortKey = Tuple[Any, ...]

SortKeyFn = Callable[[RichCompletion], SortKey]


def sort_by_prefix(prefix: str) -> SortKeyFn:
    """Sort values by prefix then alphabetically."""

    def sortkey(c: RichCompletion) -> SortKey:
        c_str = normalize(c)
        return (c_str.find(normalize(prefix)), c_str)

    return sortkey


def sort_by_prefix_display(prefix: str) -> SortKeyFn:
    def sortkey(c: RichCompletion) -> SortKey:
        c_str = normalize(c)
        display_priority = 0 if c.display else 1 if c.description else 2
        # Special case for bare `?` help.
        if c.value == "?" or c.value.startswith("--help"):
            display_priority = -1
        return (c_str.find(normalize(prefix)), display_priority, c_str)

    return sortkey


def sort_default() -> SortKeyFn:
    def sortkey(c: RichCompletion) -> SortKey:
        return (normalize(c),)

    return sortkey
