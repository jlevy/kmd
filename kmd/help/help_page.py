from kmd.commands.command_registry import all_commands
from kmd.config.logger import get_logger
from kmd.docs import (
    development,
    faq,
    getting_started,
    kmd_overview,
    motivation,
    tips_for_use_with_other_tools,
    what_is_kmd,
    workspace_and_file_formats,
)
from kmd.help.command_help import output_action_help, output_command_function_help
from kmd.text_ui.command_output import console_pager, output, output_heading, output_markdown

log = get_logger(__name__)


def output_help_page(base_actions_only: bool = False) -> None:
    from kmd.action_defs import load_all_actions

    with console_pager():

        output_markdown(str(what_is_kmd))

        output_markdown(str(motivation))

        output_markdown(str(getting_started))

        output_markdown(str(tips_for_use_with_other_tools))

        output_markdown(str(development))

        output_markdown(str(kmd_overview))

        output_markdown(str(workspace_and_file_formats))

        output_markdown(str(faq))

        output_heading("Available Commands")

        for command in all_commands().values():
            output_command_function_help(command, verbose=False)

        output_heading("Available Actions")

        actions = load_all_actions(base_only=base_actions_only)
        for action in actions.values():
            output_action_help(action, verbose=False)

        output_heading("For Additional Help")

        output("Use `help` for this help page. Use `xonfig tutorial` for xonsh help.")

        output()
