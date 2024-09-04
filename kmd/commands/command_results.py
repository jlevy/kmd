from dataclasses import dataclass
from typing import Any, List, Optional
from kmd.config.logger import get_console
from kmd.config.text_styles import COLOR_HINT, EMOJI_HINT
from kmd.lang_tools.inflection import plural
from kmd.model.locators import StorePath
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
    show_applicable_actions: bool = False
    exception: Optional[Exception] = None


def type_str(value: Optional[Any]) -> str:
    if value is None:
        return "None"
    elif isinstance(value, str):
        return f"{len(value)} chars"
    elif isinstance(value, list):
        return f"{len(value)} {plural("item", len(value))}"
    elif isinstance(value, dict):
        return f"dict size {len(value)}"
    else:
        return type(value).__name__


def print_selection(selection: List[StorePath]) -> None:
    """
    Print the current selection.
    """
    if not selection:
        output_status("No selection.")
    else:
        output_status(
            "Selected %s:\n%s",
            type_str(selection),
            fmt_lines(selection),
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


def var_hints(res: CommandResult) -> str:
    if res.result and res.selection:
        hint_str = f"{EMOJI_HINT} $result ({type_str(res.result)}) and $selection ({type_str(res.selection)}) are set"
    elif res.result:
        hint_str = f"{EMOJI_HINT} $result ({type_str(res.result)}) is set"
    elif res.selection:
        hint_str = f"{EMOJI_HINT} $selection ({type_str(res.selection)}) is set"
    else:
        hint_str = ""

    return hint_str


def print_command_result_info(res: CommandResult) -> None:
    if res.exception:
        raise res.exception

    trail_newline = False

    if res.result and res.show_result:
        print_result(res.result)
        trail_newline = True

    if res.selection and res.show_selection:
        print_selection(res.selection)
        trail_newline = True

    if res.show_applicable_actions:
        from kmd.commands import commands

        applicable_actions = commands.applicable_actions(brief=True)
        if applicable_actions:
            output_result(applicable_actions)
            trail_newline = True

    var_hint_str = var_hints(res)
    if var_hint_str:
        if not trail_newline:
            output()

        output(var_hint_str, color=COLOR_HINT)

    output()


