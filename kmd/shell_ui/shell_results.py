from typing import Any, Optional

from rich.box import SQUARE
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT, COLOR_SELECTION, CONSOLE_WRAP_WIDTH
from kmd.errors import is_fatal
from kmd.exec.command_exec import run_command
from kmd.model.args_model import fmt_loc
from kmd.model.shell_model import ShellResult
from kmd.shell_ui.shell_output import console_pager, cprint, print_result
from kmd.util.format_utils import fmt_count_items
from kmd.workspaces.selections import Selection, SelectionHistory
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)

MAX_LINES_WITHOUT_PAGING = 128


def shell_print_selection_history(
    sh: SelectionHistory, last: Optional[int] = None, after_cur: Optional[int] = None
) -> None:
    """
    Print the current selection history. Shows back last items, and forward until
    the end of the list (or `after_cur` items forward if that is provided).
    """
    n = len(sh.history)
    start_idx = max(0, sh.current_index - last) if last else 0
    end_idx = min(n, sh.current_index + after_cur) if after_cur else n
    history_slice = sh.history[start_idx:end_idx]

    if n == 0:
        content = Text("No selection history.", style=COLOR_SELECTION)
        panel_title = "Selection History"
        cprint(Panel(content, box=SQUARE, style=COLOR_SELECTION, padding=(0, 1), title=panel_title))
    else:
        table = Table(show_header=False, box=None, pad_edge=False, width=CONSOLE_WRAP_WIDTH)
        for v, selection in enumerate(history_slice):
            i = v + start_idx
            is_current = i == sh.current_index
            box_color = COLOR_SELECTION if is_current else COLOR_HINT
            content_color = "default" if is_current else COLOR_HINT

            if not selection.paths:
                selection_text = Text("No selection.", style=content_color)
            else:
                selection_text = Text(
                    "\n".join(fmt_loc(p) for p in selection.paths), style=content_color
                )

            selection_title = (
                f"$selections[{-(n - i)}]: {fmt_count_items(len(selection.paths), 'item')}"
            )
            if is_current:
                selection_title = f"Current selection: {selection_title}"

            selection_panel = Panel(
                selection_text,
                box=SQUARE,
                padding=(0, 1),
                style=box_color,
                title=Text(selection_title, style=box_color),
                title_align="left",
            )
            table.add_row(selection_panel)

        cprint(table)

    if n > 0:
        cprint("(history is in $selections)", color=COLOR_HINT)


def shell_print_selection(selection: Selection) -> None:
    """
    Print the current selection.
    """
    if not selection.paths:
        content = Text("No selection.", style="default")
    else:
        content = Text("\n".join(fmt_loc(p) for p in selection.paths), style="default")

    panel_title = f"Current selection: {fmt_count_items(len(selection.paths), 'item')}"

    cprint(
        Panel(
            content,
            box=SQUARE,
            style=COLOR_SELECTION,
            padding=(0, 1),
            title=Text(panel_title, style=COLOR_SELECTION),
            title_align="left",
        )
    )

    if selection.paths:
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
