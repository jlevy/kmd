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
from kmd.help.command_help import print_action_help, print_command_function_help
from kmd.shell.shell_output import cprint, print_heading, print_markdown, Wrap

log = get_logger(__name__)


def print_builtin_commands_help() -> None:
    for command in all_commands().values():
        print_command_function_help(command, verbose=False)


def print_actions_help(base_actions_only: bool = False) -> None:
    from kmd.action_defs import load_all_actions

    actions = load_all_actions(base_only=base_actions_only)
    for action in actions.values():
        print_action_help(action, verbose=False)


def quote_item(item: str) -> str:
    if "`" not in item:
        return f"`{item}`"
    else:
        return item


def print_see_also(commands_or_questions: List[str]) -> None:
    cprint()
    cprint("See also:", color=COLOR_EMPH)
    for item in commands_or_questions:
        cprint(quote_item(item), text_wrap=Wrap.INDENT_ONLY)


def print_manual(base_actions_only: bool = False) -> None:

    print_markdown(what_is_kmd)

    print_markdown(motivation)

    print_markdown(getting_started)

    print_markdown(tips_for_use_with_other_tools)

    print_markdown(development)

    print_markdown(kmd_overview)

    print_markdown(workspace_and_file_formats)

    print_markdown(faq)

    print_heading("Available Commands")

    print_builtin_commands_help()

    print_heading("Available Actions")

    print_actions_help(base_actions_only=base_actions_only)

    print_heading("For Additional Help")

    cprint("Use `help` for this help page. Use `xonfig tutorial` for xonsh help.")

    cprint()
