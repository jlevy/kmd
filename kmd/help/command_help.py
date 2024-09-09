from typing import List, Optional

from kmd.model.params_model import Param
from kmd.model.preconditions_model import Precondition
from kmd.text_formatting.text_formatting import DEFAULT_INDENT
from kmd.text_ui.command_output import format_name_and_description, output, output_help, Wrap


def output_command_help(
    name: str,
    description: Optional[str] = None,
    param_docs: Optional[List[Param]] = None,
    precondition: Optional[Precondition] = None,
):
    command_str = f"the `{name}` command" if name else "this command"

    output()

    if not description:
        output_help(f"Sorry, no help available for {command_str}.")
    else:
        output(format_name_and_description(name, description))

    if precondition:
        output()
        output_help("Precondition:")
        output(str(precondition), text_wrap=Wrap.WRAP_INDENT)

    if param_docs:
        output()
        output_help("Options:")
        for param in param_docs:
            desc_suffix = ""
            if param.description:
                desc_suffix = f": {param.description}"
            if param.type == bool:
                output(
                    f"--{param.name}{desc_suffix}",
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )
            else:
                output(
                    f"--{param.name}=<value>{desc_suffix}",
                    text_wrap=Wrap.HANGING_INDENT,
                    extra_indent=DEFAULT_INDENT,
                )

    output()
    output_help(
        "For more information, ask the assistant by typing a question (ending in ?) or check `kmd_help`."
    )
    output()
