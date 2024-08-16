import inspect
from inspect import Parameter
from typing import (
    Callable,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    get_origin,
    get_args,
    Union,
)
from dataclasses import dataclass

from kmd.model.params_model import ALL_COMMON_PARAMS, Param


@dataclass(frozen=True)
class FuncParam:
    name: str
    type: Type
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
                kw_args.append(func_param)
        elif param_kind == Parameter.VAR_POSITIONAL:
            pos_args.append(func_param)
        elif param_kind == Parameter.KEYWORD_ONLY:
            kw_args.append(func_param)
        elif param_kind == Parameter.VAR_KEYWORD:
            kw_args.append(func_param)

    return pos_args, kw_args


def _look_up_func_param(param: FuncParam) -> Param:
    return ALL_COMMON_PARAMS.get(param.name) or Param(param.name, type=param.type)


def _look_up_func_params(kw_params: List[FuncParam]) -> List[Param]:
    return [_look_up_func_param(func_param) for func_param in kw_params]


ParamInfo = Tuple[List[FuncParam], List[FuncParam], List[Param]]


def collect_param_info(func: Callable[..., Any]) -> ParamInfo:
    """
    Assign info on positional and keyword paramaters for a function, as well as docs for
    them (if available, matching based on paramater name), to the function's `__param_info__`
    attribute.
    """
    if not hasattr(func, "__param_info__"):
        pos_params, kw_params = inspect_function_params(func)
        func.__param_info__ = (pos_params, kw_params, _look_up_func_params(kw_params))

    return func.__param_info__


## Tests


def test_inspect_function_params():

    def func0(path: Optional[str] = None) -> List:
        return [path]

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
