import os
from typing import Optional

from kmd.commands.command_registry import kmd_command
from kmd.commands.files_commands import trash
from kmd.config.logger import get_logger, log_file_path, log_objects_dir, reset_logging
from kmd.config.settings import global_settings, LogLevel, update_global_settings
from kmd.config.setup import log_api_key_setup
from kmd.model.args_model import fmt_loc
from kmd.server import local_server
from kmd.shell.shell_output import cprint, format_name_and_description, print_status
from kmd.shell_tools.native_tools import tail_file
from kmd.shell_tools.tool_deps import tool_check
from kmd.util.format_utils import fmt_lines
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_command
def version() -> None:
    """
    Show the version of kmd.
    """
    from kmd.main import APP_VERSION

    cprint(APP_VERSION)


@kmd_command
def self_check() -> None:
    """
    Self-check kmd setup, including tools and API keys.
    """
    version()
    cprint()
    check_tools()
    cprint()
    log_api_key_setup(once=False)
    cprint()


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
def logs(follow: bool = False) -> None:
    """
    Page through the logs for the current workspace.

    :param follow: Follow the file as it grows.
    """
    tail_file(log_file_path(), follow=follow)


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
def reset_ignore_file(append: bool = False) -> None:
    """
    Reset the kmd ignore file to the default.
    """
    from kmd.file_tools.ignore_files import write_ignore

    ws = current_workspace()
    ignore_path = ws.base_dir / ws.dirs.ignore_file
    write_ignore(ignore_path, append=append)

    log.message("Rewrote kmd ignore file: %s", fmt_loc(ignore_path))


@kmd_command
def ignore_file(pattern: Optional[str] = None) -> None:
    """
    Add a pattern to the kmd ignore file, or show the current patterns
    if none is specified.
    """
    from kmd.file_tools.ignore_files import add_to_ignore
    from kmd.commands.files_commands import show

    ws = current_workspace()
    ignore_path = ws.base_dir / ws.dirs.ignore_file

    if not pattern:
        show(ignore_path)
    else:
        add_to_ignore(ignore_path, pattern)


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
def restart_server() -> None:
    """
    Restart the kmd local server.
    """
    from kmd.server.local_server import restart_server

    restart_server()


@kmd_command
def server_logs(follow: bool = False) -> None:
    """
    Show the logs from the kmd local server.

    :param follow: Follow the file as it grows.
    """
    tail_file(local_server.log_file_path(global_settings().local_server_port), follow=follow)


@kmd_command
def reload_kmd() -> None:
    """
    Reload the kmd package and all its submodules. Also restarts the local the
    local server.

    Not perfect! But sometimes useful for development.
    """
    import kmd
    from kmd.util.import_utils import recursive_reload

    module = kmd
    exclude = ["kmd.xontrib.kmd"]  # Don't reload the kmd initialization.

    def filter_func(name: str) -> bool:
        if exclude:
            for excluded_module in exclude:
                if name == excluded_module or name.startswith(excluded_module + "."):
                    log.info("Excluding reloading module: %s", name)
                    return False
        return True

    package_names = recursive_reload(module, filter_func=filter_func)
    log.info("Reloaded modules: %s", ", ".join(package_names))
    log.message("Reloaded %s modules from %s.", len(package_names), module.__name__)

    restart_server()

    # TODO Re-register commands and actions.


# TODO:
# def define_action_sequence(name: str, *action_names: str):
#     action_registry.define_action_sequence(name, *action_names)
#     log.message("Registered action sequence: %s of actions: %s", name, action_names)
