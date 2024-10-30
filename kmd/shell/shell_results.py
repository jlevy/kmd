from typing import Any, List, Optional

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT
from kmd.errors import is_fatal
from kmd.exec.command_exec import run_command
from kmd.file_storage.workspaces import current_workspace
from kmd.lang_tools.inflection import plural
from kmd.model.paths_model import fmt_loc, StorePath
from kmd.model.shell_model import ShellResult
from kmd.shell.shell_output import console_pager, cprint, print_result, print_selection
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


def shell_print_selection(selection: List[StorePath]) -> None:
    """
    Print the current selection.
    """
    if not selection:
        print_selection("No selection.")
    else:
        print_selection(
            "Selected %s:\n%s",
            type_str(selection),
            fmt_lines(fmt_loc(s) for s in selection),
        )


def shell_print_result(value: Optional[Any]) -> None:
    if value:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            str_lines = "\n".join(value)
            if len(value) > MAX_LINES_WITHOUT_PAGING:
                with console_pager():
                    print_result(str_lines)
                cprint()
            else:
                print_result(str_lines)
        else:
            print_result(str(value))


def shell_before_exec() -> None:
    """
    Code to run before executing a command.
    """
    cprint()


def handle_shell_result(res: ShellResult) -> None:
    """
    Handle the result of a command, displaying output, selection, etc.
    """
    if res.exception:
        # Nonfatal exceptions will already be logged.
        if is_fatal(res.exception):
            raise res.exception

    if res.display_command:
        log.message("Displaying result with: %s", res.display_command)
        command_output = run_command(res.display_command)
        log.info("Ignoring display command output: %s", command_output)

    if res.result and res.show_result:
        cprint()
        shell_print_result(res.result)
        cprint()
        cprint(f"({type_str(res.result)} saved as $result)", color=COLOR_HINT)

    if res.show_selection or res.suggest_actions:
        selection = current_workspace().get_selection()

        if selection and res.show_selection:
            cprint()
            shell_print_selection(selection)
            cprint()
            cprint("(saved as $selection)", color=COLOR_HINT)
            cprint()

        if selection and res.suggest_actions:
            from kmd.commands import command_defs

            command_defs.suggest_actions()
