import os
from typing import Optional

from rich import get_console

from kmd.commands.command_registry import kmd_command
from kmd.commands.files_commands import trash
from kmd.commands.selection_commands import select
from kmd.config.logger import get_logger, log_file_path, log_objects_dir, reset_logging
from kmd.config.settings import global_settings, LogLevel, update_global_settings
from kmd.config.text_styles import PROMPT_ASSIST, SPINNER
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assist_system_message_with_state, shell_context_assistance
from kmd.model.args_model import fmt_loc
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.model.shell_model import ShellResult
from kmd.server import local_server
from kmd.shell.shell_output import cprint, format_name_and_description, print_status
from kmd.shell_tools.native_tools import tail_file
from kmd.shell_tools.tool_deps import tool_check
from kmd.util.format_utils import fmt_lines
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_command
def check_tools(warn_only: bool = False) -> None:
    """
    Check that all tools are installed.
    """
    if warn_only:
        tool_check().warn_if_missing()
    else:
        cprint("Checking for required tools:")
        cprint()
        cprint(tool_check().formatted())
        cprint()
        tool_check().warn_if_missing()


@kmd_command
def logs() -> None:
    """
    Page through the logs for the current workspace.
    """
    tail_file(log_file_path())


@kmd_command
def clear_logs() -> None:
    """
    Clear the logs for the current workspace. Logs for the current workspace will be lost
    permanently!
    """
    log_path = log_file_path()
    if log_path.exists():
        with open(log_path, "w"):
            pass
    obj_dir = log_objects_dir()
    if obj_dir.exists():
        trash(obj_dir)
        os.makedirs(obj_dir, exist_ok=True)

    print_status("Logs cleared:\n%s", fmt_lines([fmt_loc(log_path)]))


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
    Print the assistant system message.
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


@kmd_command
def log_level(level: Optional[str] = None, console: bool = False, file: bool = False) -> None:
    """
    Set or show the log level. Applies to both console and file log levels unless specified.

    :param level: The log level to set. If not specified, will show current level.
    :param console: Set console log level only.
    :param file: Set file log level only.
    """
    if not console and not file:
        console = True
        file = True

    if level:
        level_parsed = LogLevel.parse(level)
        with update_global_settings() as settings:
            if console:
                settings.console_log_level = level_parsed
            if file:
                settings.file_log_level = level_parsed

        reset_logging()

    cprint()
    cprint(format_name_and_description("file_log_level", global_settings().file_log_level.name))
    cprint(
        format_name_and_description("console_log_level", global_settings().console_log_level.name)
    )
    cprint()


@kmd_command
def start_server() -> None:
    """
    Start the kmd local server.
    """
    from kmd.server.local_server import start_server

    start_server()


@kmd_command
def stop_server() -> None:
    """
    Stop the kmd local server.
    """
    from kmd.server.local_server import stop_server

    stop_server()


@kmd_command
def server_logs() -> None:
    """
    Show the logs from the kmd local server.
    """
    tail_file(local_server.log_file_path())


@kmd_command
def version() -> None:
    """
    Show the version of kmd.
    """
    from kmd.main import APP_VERSION

    cprint(APP_VERSION)


# TODO:
# def define_action_sequence(name: str, *action_names: str):
#     action_registry.define_action_sequence(name, *action_names)
#     log.message("Registered action sequence: %s of actions: %s", name, action_names)
