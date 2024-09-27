import inspect
from inspect import Parameter
from typing import Any, Callable, get_args, get_origin, List, Optional, Tuple, Type, Union

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class FuncParam:
    name: str
    type: Optional[Type]
    default: Any
    is_varargs: bool


def inspect_function_params(func: Callable[..., Any]) -> Tuple[List[FuncParam], List[FuncParam]]:
    """
    Extract parameters from a function's variable names and type annotations. Return the
    positional and keyword parameters.
    """
    signature = inspect.signature(func)
    pos_args: List[FuncParam] = []
    kw_args: List[FuncParam] = []

    for param in signature.parameters.values():
        param_name = param.name
        param_default = param.default if param.default != param.empty else None
        param_kind = param.kind

        # Get type from type annotation or default value.
        param_type: Optional[Type] = None
        if param.annotation != param.empty:
            param_type = _extract_simple_type(param.annotation)
        elif param_default is not None:
            param_type = type(param_default)

        func_param = FuncParam(
            param_name,
            param_type,
            param_default,
            param_kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD),
        )

        if param_kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
            if param.default == param.empty:
                pos_args.append(func_param)
            else:
                kw_args.append(func_param)
        elif param_kind == Parameter.VAR_POSITIONAL:
            pos_args.append(func_param)
        elif param_kind in (Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD):
            kw_args.append(func_param)

    return pos_args, kw_args


def _extract_simple_type(annotation: Any) -> Optional[Type]:
    """
    Extract a single Type from an annotation that is an explicit simple type (like `str` or
    an enum) or a simple Union (such as `str` from `Optional[str]`). Return None if it's not
    clear.
    """
    if isinstance(annotation, type):
        return annotation

    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and isinstance(non_none_args[0], type):
            return non_none_args[0]
    elif origin is not None and isinstance(origin, type):
        return origin

    return None


## Tests


def test_inspect_function_params():
    def func0(path: Optional[str] = None) -> List:
        return [path]

    def func1(
        arg1: str, arg2: str, arg3: int, option_one: bool = False, option_two: Optional[str] = None
    ) -> List:
        return [arg1, arg2, arg3, option_one, option_two]

    def func2(*paths: str, summary: Optional[bool] = False, iso_time: bool = False) -> List:
        return [paths, summary, iso_time]

    def func3(arg1: str, **keywords) -> List:
        return [arg1, keywords]

    def func4() -> List:
        return []

    params0 = inspect_function_params(func0)
    params1 = inspect_function_params(func1)
    params2 = inspect_function_params(func2)
    params3 = inspect_function_params(func3)
    params4 = inspect_function_params(func4)

    print("\ninspect:")
    print(repr(params0))
    print()
    print(repr(params1))
    print()
    print(repr(params2))
    print()
    print(repr(params3))
    print()
    print(repr(params4))

    assert params0 == ([], [FuncParam(name="path", type=str, default=None, is_varargs=False)])

    assert params1 == (
        [
            FuncParam(name="arg1", type=str, default=None, is_varargs=False),
            FuncParam(name="arg2", type=str, default=None, is_varargs=False),
            FuncParam(name="arg3", type=int, default=None, is_varargs=False),
        ],
        [
            FuncParam(name="option_one", type=bool, default=False, is_varargs=False),
            FuncParam(name="option_two", type=str, default=None, is_varargs=False),
        ],
    )

    assert params2 == (
        [FuncParam(name="paths", type=str, default=None, is_varargs=True)],
        [
            FuncParam(name="summary", type=bool, default=False, is_varargs=False),
            FuncParam(name="iso_time", type=bool, default=False, is_varargs=False),
        ],
    )

    assert params3 == (
        [FuncParam(name="arg1", type=str, default=None, is_varargs=False)],
        [FuncParam(name="keywords", type=None, default=None, is_varargs=True)],
    )

    assert params4 == ([], [])
