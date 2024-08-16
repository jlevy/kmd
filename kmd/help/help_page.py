from kmd.commands.command_registry import all_commands
from kmd.docs.topics import about_kmd, faq, workspace_and_file_formats
from kmd.text_ui.command_output import (
    format_name_and_description,
    output,
    output_heading,
    output_markdown,
)
from kmd.config.logger import get_logger

log = get_logger(__name__)


def output_help_page(base_only: bool = False) -> None:
    from kmd.action_defs import load_all_actions

    output_heading("About kmd")
    output_markdown(about_kmd.__doc__)

    output_heading("Workspace and File Formats")
    output_markdown(workspace_and_file_formats.__doc__)

    output_heading("Frequently Asked Questions")
    output_markdown(faq.__doc__)

    output_heading("Available Commands")
    for command in all_commands().values():
        doc = command.__doc__ if command.__doc__ else ""
        output(format_name_and_description(command.__name__, doc))
        output()

    output_heading("Available Actions")
    actions = load_all_actions(base_only=base_only)
    for action in actions.values():
        output(format_name_and_description(action.name, action.description))
        output()

    output_heading("More help")
    output(
        "Use `kmd_help` for this list. Use `xonfig tutorial` for xonsh help and `help()` for Python help."
    )

    output()
