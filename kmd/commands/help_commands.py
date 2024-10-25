from rich.text import Text

from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HEADING, COLOR_HINT, COLOR_LOGO, HRULE, LOGO
from kmd.help.help_page import output_see_also
from kmd.text_ui.command_output import console_pager, output, output_markdown, Wrap
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

    output()
    output(HRULE, color=COLOR_HINT)
    version = get_version_name()
    padding = " " * (len(HRULE) - len(LOGO) - len(version))
    output(Text(LOGO, style=COLOR_LOGO) + Text(padding + version, style=COLOR_HINT))
    output(HRULE, color=COLOR_HINT)
    output()
    output("Welcome to kmd.\n", color=COLOR_HEADING)
    output()
    output(welcome, text_wrap=Wrap.WRAP_FULL)
    output(HRULE, color=COLOR_HINT)


@kmd_command
def help() -> None:
    """
    Show the Kmd main help page.
    """
    # TODO: Take an argument to show help for a specific command or action.

    from kmd.help.help_page import output_help_page

    with console_pager():
        output_help_page()


@kmd_command
def why_kmd() -> None:
    """
    Show help on why Kmd was created.
    """
    from kmd.docs import motivation, what_is_kmd

    with console_pager():
        output_markdown(what_is_kmd)
        output_markdown(motivation)
        output_see_also(["help", "getting_started", "faq", "commands", "actions"])


@kmd_command
def getting_started() -> None:
    """
    Show help on getting started with Kmd.
    """
    from kmd.docs import getting_started

    with console_pager():
        output_markdown(getting_started)
        output_see_also(
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
        output_markdown(faq)

        output_see_also(["help", "commands", "actions"])


@kmd_command
def commands() -> None:
    """
    Show help on all Kmd commands.
    """
    from kmd.help.help_page import output_builtin_commands_help

    with console_pager():
        output_builtin_commands_help()
        output_see_also(["actions", "help", "faq", "What are the most important Kmd commands?"])


@kmd_command
def actions() -> None:
    """
    Show help on the full list of currently loaded actions.
    """
    from kmd.help.help_page import output_actions_help

    with console_pager():
        output_actions_help()
        output_see_also(["commands", "help", "faq", "What are the most important Kmd commands?"])
