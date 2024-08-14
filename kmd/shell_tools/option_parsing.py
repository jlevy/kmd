from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
)
from kmd.util.parse_utils import parse_key_value


@dataclass(frozen=True)
class ShellArgs:
    pos_args: List[str]
    kw_args: Dict[str, Optional[str]]
    show_help: bool = False


def parse_shell_args(args: List[str]) -> ShellArgs:
    """
    Parse shell input arguments into a ShellArgs object:

    `["foo", "--opt1", "--opt2=bar"] -> ShellArgs(pos_args=["foo"], kw_args={"opt1": True, "opt2": "bar"}, show_help=False)`
    """
    pos_args = []
    kw_args = {}
    show_help = False

    i = 0
    while i < len(args):
        if args[i].startswith("-"):
            prefix = "--" if args[i].startswith("--") else "-"
            prefix_len = len(prefix)
            key_value_str = args[i][prefix_len:]
            key, value = parse_key_value(key_value_str)
            key = key.replace("-", "_")
            if key == "help":
                show_help = True
            else:
                kw_args[key] = value if value is not None else True
            i += 1
        else:
            pos_args.append(args[i])
            i += 1

    return ShellArgs(pos_args=pos_args, kw_args=kw_args, show_help=show_help)


## Tests


def test_parse_shell_args():
    args = ["pos1", "pos2", "--key1=value1", "--key2", "pos3", "-k3=value3", "--help"]
    shell_args = parse_shell_args(args)

    assert shell_args.pos_args == [
        "pos1",
        "pos2",
        "pos3",
    ]
    assert shell_args.kw_args == {
        "key1": "value1",
        "key2": True,
        "k3": "value3",
    }
    assert shell_args.show_help == True
