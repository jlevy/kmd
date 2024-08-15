from typing import (
    Callable,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
)
from kmd.config.logger import get_logger
from kmd.help.command_help import output_command_help
from kmd.model.errors_model import InvalidCommand
from kmd.model.params_model import ALL_COMMON_PARAMS, Param
from kmd.shell_tools.function_inspect import FuncParam, inspect_function_params
from kmd.shell_tools.option_parsing import parse_shell_args

log = get_logger(__name__)


def _map_positional(
    pos_args: List[str], pos_params: List[FuncParam], kw_params: Dict[str, FuncParam]
) -> Tuple[List[Any], int]:
    """
    Map parsed positional arguments to function parameters, ensuring the number of
    arguments matches and converting types.
    """
    pos_values = []
    i = 0
    keywords_consumed = 0

    for param in pos_params:
        if param.is_var:
            pos_values.extend([param.type(arg) for arg in pos_args[i:]])
            return pos_values, 0  # All remaining args are consumed, so we can return early.
        elif i < len(pos_args):
            pos_values.append(param.type(pos_args[i]))
            i += 1
        else:
            raise InvalidCommand(f"Missing positional argument: {param.name}")

    # If there are remaining positional arguments, they will go toward keyword arguments.
    for param in kw_params.values():
        if not param.is_var and i < len(pos_args):
            pos_values.append(param.type(pos_args[i]))
            i += 1
            keywords_consumed += 1

    if i < len(pos_args):
        raise InvalidCommand(
            f"Too many arguments provided (expected {len(pos_params)}, got {len(pos_args)}): {pos_args}"
        )

    return pos_values, keywords_consumed


def _map_keyword(
    kw_args: Dict[str, Optional[str]], kw_params: Dict[str, FuncParam]
) -> Dict[str, Any]:
    """
    Map parsed keyword arguments to function parameters, converting types and handling var
    keyword arguments.
    """

    kw_values = {param.name: param.default for param in kw_params.values() if not param.is_var}
    var_kw_values = {}
    var_kw_param = None

    for param in kw_params.values():
        if param.is_var:
            var_kw_param = param
            break

    for key, value in kw_args.items():
        if key in kw_params:
            kw_values[key] = kw_params[key].type(value)  # Convert value to type.
        elif var_kw_param:
            var_kw_values[key] = value
        else:
            raise InvalidCommand(f"Unknown option: --{key}")

    if var_kw_param:
        kw_values.update(var_kw_values)

    return kw_values


def _look_up_params(kw_params: Dict[str, FuncParam]) -> Dict[str, Param]:

    def get_param(name: str, param: FuncParam) -> Param:
        return ALL_COMMON_PARAMS.get(param.name) or Param(name, type=param.type)

    return {
        name: param
        for name, param in ((name, get_param(name, param)) for name, param in kw_params.items())
        if param is not None
    }


R = TypeVar("R")


def wrap_for_shell_args(func: Callable[..., R]) -> Callable[[List[str]], Optional[R]]:
    """
    Wrap a function to accept a list of string shell arguments, parse them, and call the
    original function.
    """
    pos_params, kw_params = inspect_function_params(func)

    def wrapped(args: List[str]) -> Optional[R]:

        shell_args = parse_shell_args(args)

        pos_values, keywords_consumed = _map_positional(shell_args.pos_args, pos_params, kw_params)

        # If some positional arguments were used as keyword arguments, we need to remove
        # them from the kw_params so they don't get passed twice.
        remaining_kw_params = dict(list(kw_params.items())[keywords_consumed:])

        kw_values = _map_keyword(shell_args.kw_args, remaining_kw_params)

        log.info(
            "Mapping shell args to function params: %s -> %s -> pos_values=%s, kw_values=%s",
            args,
            shell_args,
            pos_values,
            kw_values,
        )

        param_info = _look_up_params(kw_params)

        if shell_args.show_help:
            output_command_help(func.__name__, func.__doc__, param_info)

            return None

        return func(*pos_values, **kw_values)

    wrapped.__name__ = func.__name__
    wrapped.__doc__ = func.__doc__
    return wrapped


## Tests


def test_wrap_function():

    def func1(
        arg1: str, arg2: str, arg3: int, option_one: bool = False, option_two: Optional[str] = None
    ) -> List:
        return [arg1, arg2, arg3, option_one, option_two]

    def func2(
        *paths: str, summary: Optional[bool] = False, iso_time: Optional[bool] = False
    ) -> List:
        return [paths, summary, iso_time]

    def func3(arg1: str, **keywords) -> List:
        return [arg1, keywords]

    def func4() -> List:
        return []

    wrapped_func1 = wrap_for_shell_args(func1)
    wrapped_func2 = wrap_for_shell_args(func2)
    wrapped_func3 = wrap_for_shell_args(func3)
    wrapped_func4 = wrap_for_shell_args(func4)

    print("\nwrapped:")
    print(
        wrapped_func1(["arg1_value", "arg2_value", "99", "--option_one", "--option_two=some_value"])
    )
    print(wrapped_func2(["--summary", "--iso_time", "path1", "path2", "path3"]))
    print(wrapped_func3(["arg1_value", "--extra_param=some_value"]))

    print(wrapped_func4([]))

    assert wrapped_func1(
        ["arg1_value", "arg2_value", "99", "--option_one", "--option_two=some_value"]
    ) == [
        "arg1_value",
        "arg2_value",
        99,
        True,
        "some_value",
    ]
    assert wrapped_func2(["--summary", "--iso_time", "path1", "path2", "path3"]) == [
        ("path1", "path2", "path3"),
        True,
        True,
    ]
    assert wrapped_func3(["arg1_value", "--extra_param=some_value"]) == [
        "arg1_value",
        {"extra_param": "some_value"},
    ]
    assert wrapped_func4([]) == []
