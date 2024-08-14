from typing import (
    Dict,
    List,
    Tuple,
    Optional,
)
from kmd.util.parse_utils import parse_key_value


def parse_shell_args(args: List[str]) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """
    Parse shell input arguments into positional and keyword arguments:

    `["foo", "--opt1", "--opt2=bar"] -> (["foo"], {"opt1": None, "opt2": "bar"})`
    """
    pos_args = []
    kw_args = {}

    i = 0
    while i < len(args):
        if args[i].startswith("-"):
            prefix = "--" if args[i].startswith("--") else "-"
            prefix_len = len(prefix)
            key_value_str = args[i][prefix_len:]
            key, value = parse_key_value(key_value_str)
            key = key.replace("-", "_")
            kw_args[key] = value
            i += 1
        else:
            pos_args.append(args[i])
            i += 1

    return pos_args, kw_args


## Tests


def test_parse_shell_args():
    args = ["pos1", "pos2", "--key1=value1", "--key2", "pos3", "-k3=value3"]
    pos_args, kw_args = parse_shell_args(args)

    assert pos_args == [
        "pos1",
        "pos2",
        "pos3",
    ]
    assert kw_args == {
        "key1": "value1",
        "key2": None,
        "k3": "value3",
    }
