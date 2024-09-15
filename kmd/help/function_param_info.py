from dataclasses import replace
from typing import Any, Callable, List

from kmd.help.docstrings import parse_docstring
from kmd.model.params_model import ALL_COMMON_PARAMS, Param
from kmd.shell_tools.function_inspect import FuncParam, inspect_function_params


def _look_up_param_docs(func: Callable[..., Any], kw_params: List[FuncParam]) -> List[Param]:

    def look_up(func: Callable[..., Any], func_param: FuncParam) -> Param:
        name = func_param.name
        param = ALL_COMMON_PARAMS.get(name)
        if not param:
            param = Param(name, type=func_param.type or str)

        # Also check the docstring for a description of this parameter.
        docstring = parse_docstring(func.__doc__ or "")
        docstring_params = docstring.param

        if name in docstring_params:
            param = replace(param, description=docstring_params[name])

        return param

    return [look_up(func, func_param) for func_param in kw_params]


def annotate_param_info(func: Callable[..., Any]) -> List[Param]:
    """
    Inspect the types on the positional and keyword paramaters for a function, as well as docs for
    them. Matching param info based on matching names in the global paramater docs as well. Also
    look at docstrings with parameter info. Cache the result on the function's `__param_info__`
    attribute.
    """
    if not hasattr(func, "__param_info__"):
        pos_params, kw_params = inspect_function_params(func)

        # Only savaing param info on keyword params for now since for most commands the
        # positional arguments are kind of self-evident.
        param_info = _look_up_param_docs(func, kw_params)

        func.__param_info__ = param_info

    return func.__param_info__
