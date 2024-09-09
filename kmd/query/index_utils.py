from functools import partial
from types import NoneType
from typing import Any, Callable, Dict, List, Sequence

from kmd.config.logger import get_logger


log = get_logger(__name__)


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, str]:
    """
    Flatten a dict with nexted structure to a single level.
    """
    items: List[tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.append((f"{new_key}{sep}{i}", item))
        else:
            items.append((new_key, v))
    return dict(items)


def drop_non_atomic(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drop values that are not atomic (str, int, float, None).
    """
    allowed_types = (str, int, float, NoneType)
    return {k: v for k, v in d.items() if isinstance(v, allowed_types)}


def tiktoken_tokenizer(model: str = "gpt-4o") -> Callable[[str], Sequence[int]]:
    import tiktoken

    enc = tiktoken.encoding_for_model(model)
    tokenizer = partial(enc.encode, allowed_special="all")
    return tokenizer
