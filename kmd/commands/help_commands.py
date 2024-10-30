from rich.text import Text

from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.config.text_styles import (
    BOX_BOTTOM,
    BOX_MID,
    BOX_PREFIX,
    BOX_TOP,
    COLOR_HEADING,
    COLOR_HINT,
    COLOR_LOGO,
    LOGO,
)
from kmd.help.help_page import print_see_also
from kmd.shell.shell_output import console_pager, cprint, print_markdown, Wrap
from kmd.version import get_version_name

log = get_logger(__name__)


HELP_COMMANDS = [
    "welcome",
    "help",
    "why_kmd",
    "getting_started",
    "commands",
    "faq",
    "commands",
    "actions",
]


@kmd_command
def welcome() -> None:
    """
    Print a welcome message.
    """
    from kmd.docs import welcome

    cprint()
    cprint(BOX_TOP, color=COLOR_HINT)
    version = get_version_name()
    padding = " " * (len(BOX_TOP) - len(BOX_PREFIX) - len(LOGO) - len(version))
    cprint(
        Text(LOGO, style=COLOR_LOGO) + Text(padding + version, style=COLOR_HINT),
        extra_indent=BOX_PREFIX,
    )
    cprint(BOX_MID, color=COLOR_HINT)
    cprint(extra_indent=BOX_PREFIX)
    cprint(Text("Welcome to Kmd.", style=COLOR_HEADING), extra_indent=BOX_PREFIX)
    cprint(extra_indent=BOX_PREFIX)
    cprint(welcome, text_wrap=Wrap.WRAP_FULL, extra_indent=BOX_PREFIX)
    cprint(BOX_BOTTOM, color=COLOR_HINT)


@kmd_command
def help() -> None:
    """
    Show the Kmd main help page.
    """
    # TODO: Take an argument to show help for a specific command or action.

    from kmd.help.help_page import print_help_page

    with console_pager():
        print_help_page()


@kmd_command
def why_kmd() -> None:
    """
    Show help on why Kmd was created.
    """
    from kmd.docs import motivation, what_is_kmd

    with console_pager():
        print_markdown(what_is_kmd)
        print_markdown(motivation)
        print_see_also(["help", "getting_started", "faq", "commands", "actions"])


@kmd_command
def installation() -> None:
    """
    Show help on installing Kmd.
    """
    from kmd.docs import installation

    with console_pager():
        print_markdown(installation)
        print_see_also(
            [
                "What is Kmd?",
                "What can I do with Kmd?",
                "getting_started",
                "What are the most important Kmd commands?",
                "commands",
                "actions",
                "check_tools",
                "faq",
            ]
        )


@kmd_command
def getting_started() -> None:
    """
    Show help on getting started using Kmd.
    """
    from kmd.docs import getting_started

    with console_pager():
        print_markdown(getting_started)
        print_see_also(
            [
                "What is Kmd?",
                "What can I do with Kmd?",
                "What are the most important Kmd commands?",
                "commands",
                "actions",
                "check_tools",
                "faq",
            ]
        )


@kmd_command
def faq() -> None:
    """
    Show the Kmd FAQ.
    """
    from kmd.docs import faq

    with console_pager():
        print_markdown(faq)

        print_see_also(["help", "commands", "actions"])


@kmd_command
def commands() -> None:
    """
    Show help on all Kmd commands.
    """
    from kmd.help.help_page import print_builtin_commands_help

    with console_pager():
        print_builtin_commands_help()
        print_see_also(["actions", "help", "faq", "What are the most important Kmd commands?"])


@kmd_command
def actions() -> None:
    """
    Show help on the full list of currently loaded actions.
    """
    from kmd.help.help_page import print_actions_help

    with console_pager():
        print_actions_help()
        print_see_also(["commands", "help", "faq", "What are the most important Kmd commands?"])
