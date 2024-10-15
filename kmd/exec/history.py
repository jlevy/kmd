from typing import Any, Callable

from kmd.file_formats.chat_format import append_chat_message, ChatMessage, ChatRole
from kmd.file_storage.workspaces import current_workspace
from kmd.model.commands_model import Command


def record_command(command: Command | str):
    ws = current_workspace()
    history_file = ws.dirs.shell_history
    if isinstance(command, str):
        command_str = command
    else:
        command_str = command.command_str()

    command_str = command_str.strip()
    if not command_str:
        return

    append_chat_message(history_file, ChatMessage(ChatRole.command, command_str))


def wrap_with_history(func: Callable) -> Callable:
    """
    Wrap a function to record the command in the shell history.
    """

    def wrapper(*args, **kwargs) -> Any:
        record_command(Command.from_obj(func, args=args, options=kwargs))
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__wrapped__ = func.__wrapped__ if hasattr(func, "__wrapped__") else func

    return wrapper
