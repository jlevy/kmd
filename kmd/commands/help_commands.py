from rich.box import SQUARE

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from kmd.action_defs import look_up_action
from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_HINT, CONSOLE_WRAP_WIDTH, LOGO, STYLE_LOGO
from kmd.docs.assemble_source_code import read_source_code
from kmd.errors import FileNotFound
from kmd.help.command_help import explain_command
from kmd.help.help_page import print_see_also
from kmd.model.language_models import DEFAULT_BASIC_LLM
from kmd.shell_ui.rich_markdown_custom import Markdown
from kmd.shell_ui.shell_output import console_pager, cprint, print_code_block, print_markdown
from kmd.version import get_version_name

log = get_logger(__name__)


@kmd_command
def welcome() -> None:
    """
    Print a welcome message.
    """
    from kmd.docs import welcome

    version = get_version_name()
    # Create header with logo and right-justified version

    separator = " " + "─" * (CONSOLE_WRAP_WIDTH - len(LOGO) - len(version) - 2 - 3 - 3) + " "
    header = Text.assemble(
        Text(LOGO, style=STYLE_LOGO),
        Text(separator),
        Text(version, style=COLOR_HINT, justify="right"),
    )
    welcome_group = Group(
        Markdown(str(welcome)),
    )

    cprint()
    cprint(
        Panel(
            welcome_group,
            title=header,
            title_align="left",
            style="none",
            padding=(1, 1),
            box=SQUARE,
        )
    )


@kmd_command
def help() -> None:
    """
    Show the Kmd main help page.
    """
    # TODO: Take an argument to show help for a specific command or action.

    from kmd.help.help_page import print_manual

    with console_pager():
        print_manual()


@kmd_command
def why_kmd() -> None:
    """
    Show help on why Kmd was created.
    """
    from kmd.docs import philosophy_of_kmd, what_is_kmd

    with console_pager():
        print_markdown(what_is_kmd)
        print_markdown(philosophy_of_kmd)
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


@kmd_command
def action_source_code(action_name: str) -> None:
    """
    Show the source code for an action.
    """

    action = look_up_action(action_name)
    source_path = getattr(action, "__source_path__", None)
    if not source_path:
        raise FileNotFound(f"No source path found for action `{action_name}`")

    source_code = read_source_code(source_path)
    print_code_block(source_code, format="python")


@kmd_command
def explain(text: str, no_assistant: bool = False) -> None:
    """
    Give help on a command or action.  If `no_assistant` is True then will not use the
    assistant if the command or text is not recognized.
    """
    model = None if no_assistant else DEFAULT_BASIC_LLM
    explain_command(text, assistant_model=model)


HELP_COMMANDS = [
    welcome,
    help,
    why_kmd,
    getting_started,
    faq,
    commands,
    actions,
]
