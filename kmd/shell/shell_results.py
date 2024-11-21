from typing import Any, Optional

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT, COLOR_SELECTION
from kmd.errors import is_fatal
from kmd.exec.command_exec import run_command
from kmd.model.shell_model import ShellResult
from kmd.shell.shell_output import (
    console_pager,
    cprint,
    print_hrule,
    print_result,
    print_selection,
    print_style,
    Style,
    Wrap,
)
from kmd.util.format_utils import fmt_count_items
from kmd.workspaces.selections import Selection, SelectionHistory
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)

MAX_LINES_WITHOUT_PAGING = 128


def shell_print_selection_history(
    sh: SelectionHistory, last: Optional[int] = None, after_cur: int = 2
) -> None:
    """
    Print the current selection history.
    """
    with print_style(Style.BOX, color=COLOR_SELECTION):
        n = len(sh.history)
        start_idx = max(0, sh.current_index - last) if last else 0
        end_idx = min(n, sh.current_index + after_cur) if last else n
        history_slice = sh.history[start_idx:end_idx]

        if n == 0:
            print_selection("No selection history.")
        else:
            for v, selection in enumerate(history_slice):
                i = v + start_idx
                is_current = i == sh.current_index
                color = COLOR_SELECTION if is_current else COLOR_HINT
                if not selection.paths:
                    cprint("No selection.", color=color)
                else:
                    if is_current:
                        cprint("current: ", color=COLOR_SELECTION)
                    cprint(
                        "$selections[%s]: %s",
                        -(n - i),
                        selection.as_str(),
                        color=color,
                        text_wrap=Wrap.NONE,
                    )
                if i < n - 1:
                    print_hrule(color=COLOR_SELECTION)
    if n > 0:
        cprint(
            "(history is in $selections)",
            color=COLOR_HINT,
        )


def shell_print_selection(selection: Selection) -> None:
    """
    Print the current selection.
    """
    if not selection.paths:
        with print_style(Style.BOX, color=COLOR_SELECTION):
            print_selection("No selection.")
    else:
        with print_style(Style.BOX, color=COLOR_SELECTION):
            print_selection(
                "Current selection: %s",
                selection.as_str(),
            )
        cprint("(in $selection)", color=COLOR_HINT)


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
        cprint(f"({fmt_count_items(len(res.result), 'item')} in $result)", color=COLOR_HINT)

    if res.show_selection or res.suggest_actions:
        selection = current_workspace().selections.current

        if res.show_selection:
            cprint()
            shell_print_selection(selection)

        if selection and res.suggest_actions:
            from kmd.commands.workspace_commands import suggest_actions

            cprint()
            suggest_actions()
