import inspect
from inspect import Parameter
from typing import (
    Callable,
    Any,
    Dict,
    List,
    Tuple,
    Type,
    get_origin,
    get_args,
    Union,
)
from dataclasses import dataclass


@dataclass(frozen=True)
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
