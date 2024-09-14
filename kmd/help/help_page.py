from kmd.commands.command_registry import all_commands
from kmd.config.logger import get_console, get_logger
from kmd.docs.topics import about_kmd, faq, workspace_and_file_formats
from kmd.help.command_help import output_action_help, output_command_function_help
from kmd.text_ui.command_output import (
    output,
    output_heading,
    output_markdown,
)
from kmd.util.type_utils import not_none

log = get_logger(__name__)


def output_help_page(base_only: bool = False) -> None:
    from kmd.action_defs import load_all_actions

    with get_console().pager(styles=True):
        output_markdown(not_none(about_kmd.__doc__))

        output_markdown(not_none(workspace_and_file_formats.__doc__))

        output_markdown(not_none(faq.__doc__))

        output_heading("Available Commands")
        for command in all_commands().values():
            output_command_function_help(command, verbose=False)

        output_heading("Available Actions")
        actions = load_all_actions(base_only=base_only)
        for action in actions.values():
            output_action_help(action, verbose=False)
            output()

        output_heading("More help")
        output(
            "Use `kmd_help` for this list. Use `xonfig tutorial` for xonsh help and `help()` for Python help."
        )

        output()
