from typing import List

from kmd.commands.command_registry import all_commands
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_EMPH
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
from kmd.shell.shell_output import output, output_heading, output_markdown, Wrap

log = get_logger(__name__)


def output_builtin_commands_help() -> None:
    for command in all_commands().values():
        output_command_function_help(command, verbose=False)


def output_actions_help(base_actions_only: bool = False) -> None:
    from kmd.action_defs import load_all_actions

    actions = load_all_actions(base_only=base_actions_only)
    for action in actions.values():
        output_action_help(action, verbose=False)


def output_see_also(commands_or_questions: List[str]) -> None:
    def quote_item(item: str) -> str:
        if "`" not in item:
            return f"`{item}`"
        else:
            return item

    output()
    output("See also:", color=COLOR_EMPH)
    for item in commands_or_questions:
        output(quote_item(item), text_wrap=Wrap.INDENT_ONLY)


def output_help_page(base_actions_only: bool = False) -> None:

    output_markdown(what_is_kmd)

    output_markdown(motivation)

    output_markdown(getting_started)

    output_markdown(tips_for_use_with_other_tools)

    output_markdown(development)

    output_markdown(kmd_overview)

    output_markdown(workspace_and_file_formats)

    output_markdown(faq)

    output_heading("Available Commands")

    output_builtin_commands_help()

    output_heading("Available Actions")

    output_actions_help(base_actions_only=base_actions_only)

    output_heading("For Additional Help")

    output("Use `help` for this help page. Use `xonfig tutorial` for xonsh help.")

    output()
