from kmd.action_defs import look_up_action
from kmd.commands.command_registry import look_up_command
from kmd.model.commands_model import Command, CommandType
from kmd.model.output_model import CommandOutput
from kmd.shell_tools.action_wrapper import ShellCallableAction


def run_command(command: Command) -> CommandOutput:
    """
    Run a command or action (for cases where we want to support arbitrary commands).
    """
    if command.type == CommandType.action:
        action = look_up_action(command.name)
        return ShellCallableAction(action)(command.args)
    elif command.type == CommandType.function:
        func = look_up_command(command.name)
        return func(command.args, command.options)
    else:
        raise ValueError(f"Unknown command type: {command.type}")
