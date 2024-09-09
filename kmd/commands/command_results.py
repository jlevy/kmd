from dataclasses import dataclass
from typing import Any, List, Optional

from kmd.config.logger import get_console
from kmd.config.text_styles import COLOR_HINT
from kmd.lang_tools.inflection import plural
from kmd.model.arguments_model import StorePath
from kmd.text_formatting.text_formatting import fmt_lines
from kmd.text_ui.command_output import output, output_result, output_status

MAX_INLINE_LENGTH = 128


@dataclass(frozen=True)
class CommandResult:
    """
    Everything needed to display the result of a command.
    """

    result: Optional[Any] = None
    selection: Optional[List[StorePath]] = None
    show_result: bool = False
    show_selection: bool = False
    suggest_actions: bool = False
    exception: Optional[Exception] = None


def type_str(value: Optional[Any]) -> str:
    if value is None:
        return "None"
    elif isinstance(value, str):
        return f"{len(value)} chars"
    elif isinstance(value, list):
        return f"{len(value)} {plural('item', len(value))}"
    elif isinstance(value, dict):
        return f"dict size {len(value)}"
    else:
        return type(value).__name__


def print_selection(selection: List[StorePath]) -> None:
    """
    Print the current selection.
    """
    if not selection:
        output_status("No selection.", extra_newlines=False)
    else:
        output_status(
            "Selected %s:\n%s",
            type_str(selection),
            fmt_lines(selection),
            extra_newlines=False,
        )


def print_result(value: Optional[Any]) -> None:
    if value:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            str_lines = "\n".join(value)
            if len(value) > MAX_INLINE_LENGTH:
                with get_console().pager():
                    output_result(str_lines)
                output()
            else:
                output_result(str_lines)
        else:
            output_result(str(value))


def print_command_result_info(res: CommandResult) -> None:
    if res.exception:
        raise res.exception

    if res.result and res.show_result:
        output()
        print_result(res.result)
        output()
        output(f"({type_str(res.result)} saved as $result)", color=COLOR_HINT)

    if res.selection and res.show_selection:
        output()
        print_selection(res.selection)
        output()
        output("(saved as $selection)", color=COLOR_HINT)
        output()

    if res.suggest_actions:
        from kmd.commands import commands

        commands.suggest_actions()
