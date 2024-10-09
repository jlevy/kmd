from kmd.action_defs import look_up_action
from kmd.commands.command_registry import look_up_command
from kmd.model.commands_model import Command
from kmd.model.output_model import CommandOutput
from kmd.shell_tools.action_wrapper import ShellCallableAction


def run_command(command: Command) -> CommandOutput:
    """
    Run a generic command, which could be invoking the assistant, an action,
    or a built-in command function.

    Note this is one of two places we invoke commands and actions. We also use direct
    invocation in xonsh. But in both cases we do the same thing for each.
    """
    # Try looking first for commands with this name.
    func = look_up_command(command.name)
    if func:
        return func(command.args, command.options)
    else:
        # Will raise ActionNotFound if we can't find command or action.
        action = look_up_action(command.name)
        return ShellCallableAction(action)(command.args)
