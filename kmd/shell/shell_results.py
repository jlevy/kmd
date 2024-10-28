from typing import Any, List, Optional

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT
from kmd.errors import is_fatal
from kmd.exec.command_exec import run_command
from kmd.file_storage.workspaces import current_workspace
from kmd.lang_tools.inflection import plural
from kmd.model.paths_model import fmt_shell_path, StorePath
from kmd.model.shell_model import ShellResult
from kmd.shell.shell_output import console_pager, output, output_result, output_selection
from kmd.util.format_utils import fmt_lines

log = get_logger(__name__)

MAX_LINES_WITHOUT_PAGING = 128


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
        output_selection("No selection.", extra_newlines=False)
    else:
        output_selection(
            "Selected %s:\n%s",
            type_str(selection),
            fmt_lines(fmt_shell_path(s) for s in selection),
            extra_newlines=False,
        )


def print_result(value: Optional[Any]) -> None:
    if value:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            str_lines = "\n".join(value)
            if len(value) > MAX_LINES_WITHOUT_PAGING:
                with console_pager():
                    output_result(str_lines)
                output()
            else:
                output_result(str_lines)
        else:
            output_result(str(value))


def handle_shell_result(res: ShellResult) -> None:
    if res.exception:
        # Nonfatal exceptions will already be logged.
        if is_fatal(res.exception):
            raise res.exception

    if res.display_command:
        log.message("Displaying result with: %s", res.display_command)
        command_output = run_command(res.display_command)
        log.info("Ignoring display command output: %s", command_output)

    if res.result and res.show_result:
        output()
        print_result(res.result)
        output()
        output(f"({type_str(res.result)} saved as $result)", color=COLOR_HINT)

    if res.show_selection or res.suggest_actions:
        selection = current_workspace().get_selection()

        if selection and res.show_selection:
            output()
            print_selection(selection)
            output()
            output("(saved as $selection)", color=COLOR_HINT)
            output()

        if selection and res.suggest_actions:
            from kmd.commands import command_defs

            command_defs.suggest_actions()
