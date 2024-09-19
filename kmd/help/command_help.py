from typing import List, Optional

from kmd.commands.command_registry import CommandFunction
from kmd.help.docstrings import parse_docstring
from kmd.help.function_param_info import annotate_param_info
from kmd.model.actions_model import Action
from kmd.model.params_model import Param, RUNTIME_ACTION_PARAMS
from kmd.model.preconditions_model import Precondition
from kmd.text_ui.command_output import format_name_and_description, output, output_help, Wrap
from kmd.util.format_utils import DEFAULT_INDENT


def _output_command_help(
    name: str,
    description: Optional[str] = None,
    param_info: Optional[List[Param]] = None,
    precondition: Optional[Precondition] = None,
    verbose: bool = True,
):
    command_str = f"the `{name}` command" if name else "this command"

    output()

    if not description:
        output_help(f"Sorry, no help available for {command_str}.")
    else:
        docstring = parse_docstring(description)

        output(format_name_and_description(name, docstring.body))

        if precondition:
            output()
            output(
                "Precondition: " + str(precondition),
                text_wrap=Wrap.HANGING_INDENT,
                extra_indent=DEFAULT_INDENT,
            )

        if param_info:
            output()
            output("Options:", extra_indent=DEFAULT_INDENT)
            for param in param_info:

                if param.type == bool:
                    param_doc = f"--{param.name}"
                else:
                    param_doc = f"--{param.name}=<value>"

                if param.name in docstring.param:
                    param_desc = docstring.param[param.name]
                elif param.description:
                    param_desc = param.description
                else:
                    param_desc = ""

                if param_desc:
                    param_doc += f": {param_desc}"

                output(
                    param_doc,
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )

    if verbose:
        output()
        output_help(
            "For more information, ask the assistant by typing a question (ending in ?) or check `help`."
        )
        output()


def output_command_function_help(command: CommandFunction, verbose: bool = True):
    param_info = annotate_param_info(command)

    _output_command_help(
        command.__name__,
        command.__doc__ if command.__doc__ else "",
        param_info=param_info,
        verbose=verbose,
    )


def output_action_help(action: Action, verbose: bool = True):
    params = []
    if verbose:
        params = action.params() + list(RUNTIME_ACTION_PARAMS.values())

    _output_command_help(
        action.name,
        action.description,
        param_info=params,
        precondition=action.precondition,
        verbose=verbose,
    )
