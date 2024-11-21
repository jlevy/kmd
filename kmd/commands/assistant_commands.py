from typing import Optional

from rich import get_console

from kmd.commands.command_registry import kmd_command
from kmd.commands.files_commands import trash
from kmd.commands.selection_commands import select
from kmd.config.logger import get_logger
from kmd.config.text_styles import PROMPT_ASSIST, SPINNER
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assist_system_message_with_state, shell_context_assistance
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.shell_model import ShellResult
from kmd.shell_tools.native_tools import tail_file
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_command
def assist(input: Optional[str] = None) -> None:
    """
    Invoke the kmd assistant. You don't normally need this command as it is the same as just
    asking a question (a question ending with ?) on the kmd console.
    """
    if not input:
        input = prompt_simple_string(
            "What do you need help with? (Ask any question or press enter to see main `help` page.)",
            prompt_symbol=PROMPT_ASSIST,
        )
        if not input.strip():
            help()
            return
    with get_console().status("Thinking…", spinner=SPINNER):
        shell_context_assistance(input)


@kmd_command
def assistant_system_message(skip_api: bool = False) -> ShellResult:
    """
    Save the assistant system message. Useful for debugging.
    """

    item = Item(
        type=ItemType.export,
        title="Assistant System Message",
        format=Format.markdown,
        body=assist_system_message_with_state(skip_api=skip_api),
    )
    ws = current_workspace()
    store_path = ws.save(item, as_tmp=True)

    log.message("Saved assistant system message to %s", store_path)

    select(store_path)

    return ShellResult(show_selection=True)


@kmd_command
def assistant_history() -> None:
    """
    Show the assistant history for the current workspace.
    """
    ws = current_workspace()
    tail_file(ws.base_dir / ws.dirs.assistant_history_yml)


@kmd_command
def clear_assistant() -> None:
    """
    Clear the assistant history for the current workspace. Old history file will be
    moved to the trash.
    """
    ws = current_workspace()
    trash(ws.base_dir / ws.dirs.assistant_history_yml)
