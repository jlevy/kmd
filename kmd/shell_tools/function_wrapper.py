import inspect
from inspect import Parameter
from typing import (
    Callable,
    Any,
    Dict,
    List,
    Tuple,
    Optional,
    Type,
    get_origin,
    get_args,
    Union,
    TypeVar,
)
from dataclasses import dataclass
from kmd.model.errors_model import InvalidCommand
from kmd.shell_tools.option_parsing import parse_shell_args


@dataclass
class FuncParam:
    name: str
    type: Type
    default: Any
    is_var: bool


def inspect_function_params(
    func: Callable[..., Any]
) -> Tuple[List[FuncParam], Dict[str, FuncParam]]:
    """
    Extract parameters from a function's variable names and type annotations. Return the
    positional and keyword parameters.
    """
    signature = inspect.signature(func)
    pos_args: List[FuncParam] = []
    kw_args: Dict[str, FuncParam] = {}

    for param in signature.parameters.values():
        param_name = param.name
        param_default = param.default
        if param.default == param.empty:
            param_default = None
        param_kind = param.kind

        # Get type from type annotation or default value.
        if param.annotation != param.empty:
            param_type = param.annotation
        elif param.default != param.empty and param.default is not None:
            param_type = type(param.default)
        else:
            param_type = None
        # Unwrap Optional type.
        if get_origin(param_type) is Union:
            param_type = next(
                (arg for arg in get_args(param_type) if arg is not type(None)),
                str,
            )
        if param_type is not None and not isinstance(param_type, type):
            param_type = type(param_type)

        func_param = FuncParam(
            param_name,
            param_type,
            param_default,
            param_kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD),
        )

        if param_kind in (
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
        ):
            if param.default == param.empty:
                pos_args.append(func_param)
            else:
                kw_args[param_name] = func_param
        elif param_kind == Parameter.VAR_POSITIONAL:
            pos_args.append(func_param)
        elif param_kind == Parameter.KEYWORD_ONLY:
            kw_args[param_name] = func_param
        elif param_kind == Parameter.VAR_KEYWORD:
            kw_args[param_name] = func_param

    return pos_args, kw_args


def _map_positional(pos_args: List[str], pos_params: List[FuncParam]) -> List[Any]:
    """
    Map parsed positional arguments to function parameters, ensuring the number of arguments matches and converting types.
    """
    pos_values = []
    i = 0

    for param in pos_params:
        if param.is_var:
            pos_values.extend([param.type(arg) for arg in pos_args[i:]])
            return pos_values  # All remaining args are consumed, so we can return early.
        elif i < len(pos_args):
            pos_values.append(param.type(pos_args[i]))
            i += 1
        else:
            raise InvalidCommand(f"Missing positional argument: {param.name}")

    if i < len(pos_args):
        raise InvalidCommand(
            f"Too many arguments provided (expected {len(pos_params)}, got {len(pos_args)}): {pos_args}"
        )

    return pos_values


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
            if value is None and isinstance(kw_params[key].default, bool):
                kw_values[key] = True  # Handle boolean options.
            else:
                kw_values[key] = kw_params[key].type(value)  # Convert value to type.
        elif var_kw_param:
            var_kw_values[key] = value
        else:
            raise InvalidCommand(f"Unknown option: --{key}")

    if var_kw_param:
        kw_values.update(var_kw_values)

    return kw_values


R = TypeVar("R")


def wrap_for_shell_args(func: Callable[..., R]) -> Callable[[List[str]], R]:
    """
    Wrap a function to accept a list of string shell arguments, parse them, and call the
    original function.
    """
    pos_params, kw_params = inspect_function_params(func)

    def wrapped(args: List[str]) -> R:
        pos_args, kw_args = parse_shell_args(args)
        pos_values = _map_positional(pos_args, pos_params)
        kw_values = _map_keyword(kw_args, kw_params)

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

    params1 = inspect_function_params(func1)
    params2 = inspect_function_params(func2)
    params3 = inspect_function_params(func3)
    params4 = inspect_function_params(func4)

    print("\ninspect:")
    print()
    print(repr(params1))
    print()
    print(repr(params2))
    print()
    print(repr(params3))
    print()
    print(repr(params4))

    assert params1 == (
        [
            FuncParam(name="arg1", type=str, default=None, is_var=False),
            FuncParam(name="arg2", type=str, default=None, is_var=False),
            FuncParam(name="arg3", type=int, default=None, is_var=False),
        ],
        {
            "option_one": FuncParam(name="option_one", type=bool, default=False, is_var=False),
            "option_two": FuncParam(name="option_two", type=str, default=None, is_var=False),
        },
    )

    assert params2 == (
        [
            FuncParam(name="paths", type=str, default=None, is_var=True),
        ],
        {
            "summary": FuncParam(name="summary", type=bool, default=False, is_var=False),
            "iso_time": FuncParam(name="iso_time", type=bool, default=False, is_var=False),
        },
    )

    assert params3 == (
        [
            FuncParam(name="arg1", type=str, default=None, is_var=False),
        ],
        {"keywords": FuncParam(name="keywords", type=None, default=None, is_var=True)},
    )

    assert params4 == ([], {})

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
