"""
Launch xonsh with kmd extensions and customizations.
"""

from rich import get_console
import kmd.config.lazy_imports  # noqa: F401
import re
import shlex
from os.path import expanduser
from typing import List, Optional
import xonsh.main
from xonsh.main import events
from xonsh.shell import Shell
from xonsh.main import premain, postmain
from xonsh.built_ins import XSH
from xonsh.execer import Execer
from xonsh.xontribs import xontribs_load
from kmd.config.logger import get_logger
from kmd.config.setup import setup
from kmd.text_ui.command_output import output, output_assistance
from kmd.assistant.assistant import assistance
from kmd.text_ui.text_styles import SPINNER


# Ensure logging is set up before anything else.
setup()

log = get_logger(__name__)

USE_CUSTOM_SHELL = True

XONSH_SHOW_TRACEBACK = True

xonshrc_init_script = """
# Auto-load of kmd:
# This only activates if xonsh is invoked as kmdsh.
xontrib load kmd
"""

xontrib_command = xonshrc_init_script.splitlines()[1].strip()

xonshrc_path = expanduser("~/.xonshrc")


def is_xontrib_installed(file_path):
    try:
        with open(file_path, "r") as file:
            for line in file:
                if xontrib_command == line.strip():
                    return True
    except FileNotFoundError:
        return False
    return False


def install_to_xonshrc():
    """
    Script to add kmd xontrib to the .xonshrc file.
    Not necessary if we are running our own customized shell (the default).
    """
    # Append the command to the file if not already present.
    if not is_xontrib_installed(xonshrc_path):
        with open(xonshrc_path, "a") as file:
            file.write(xonshrc_init_script)
        print(f"Updating your {xonshrc_path} to auto-run kmd when xonsh is invoked as kmdsh.")
    else:
        pass


def check_for_assistance_command(line: str) -> Optional[str]:
    """
    Is this a query to the assistant?
    Checks for phrases ending in a ? or a period, or starting with a ?.
    """
    line = line.strip()
    if re.search(r"\b\w+\.$", line) or re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()


# Base shell can be ReadlineShell or PromptToolkitShell.
from xonsh.ptk_shell.shell import PromptToolkitShell  # or ReadlineShell


class CustomShell(PromptToolkitShell):
    """
    Note event hooks in xonsh don't let you disable xonsh's processing, so we use a custom shell.
    """

    def default(self, line, raw_line=None):
        assist_query = check_for_assistance_command(line)
        if assist_query:
            try:
                with get_console().status("Thinking…", spinner=SPINNER):
                    output_assistance(assistance(line))
            except Exception as e:
                log.error(f"Sorry, could not get assistance: {e}")
                log.info(e, exc_info=True)
        else:
            # Call xonsh shell.
            super().default(line)


@events.on_command_not_found
def not_found(cmd: List[str]):
    # Don't call assistant on one-word typos. It's annoying.
    if len(cmd) >= 2:
        output(f"Command not found. Getting assistance…")
        with get_console().status("", spinner=SPINNER):
            output_assistance(
                assistance(
                    f"""
                    The user just typed the following command, but it was not found:

                    {" ".join(cmd)}

                    Please give them a brief suggestion of possible correct commands
                    and how they can get more help with `kmd_help` or any question
                    ending with ? in the terminal.
                    """,
                    fast=True,
                )
            )


def start_custom_xonsh(single_command: Optional[str] = None):
    # Setup for a xonsh shell, customizing just the shell itself.
    args = premain(None)  # No xonsh args.
    ctx = {}
    execer = Execer(
        filename="<stdin>",
        debug_level=0,
        scriptcache=True,
        cacheall=False,
    )
    XSH.load(ctx=ctx, execer=execer, inherit_env=True)
    XSH.shell = Shell(execer=execer)  # type: ignore
    XSH.shell.shell = CustomShell(execer=execer, ctx=ctx)

    XSH.env["XONSH_INTERACTIVE"] = False if single_command else True  # type: ignore
    XSH.env["XONSH_SHOW_TRACEBACK"] = XONSH_SHOW_TRACEBACK  # type: ignore

    ctx["__name__"] = "__main__"
    events.on_post_init.fire()
    events.on_pre_cmdloop.fire()

    # Load kmd xontrib for rest of kmd functionality.
    xontribs_load(["kmd"])

    # Main loop.
    try:
        if single_command:
            # Run a command.
            XSH.shell.shell.default(single_command)
        else:
            XSH.shell.shell.cmdloop()
    finally:
        postmain(args)


def run_shell(single_command: Optional[str] = None):
    if USE_CUSTOM_SHELL:
        start_custom_xonsh(single_command)
    else:
        # For a regular xonsh init without a customized shell.
        # When running in regular xonsh we need to load kmd xontrib via xonshrc.
        install_to_xonshrc()
        xonsh.main.main()


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch the kmd shell. If a single command is provided, it will run and exit."
    )
    parser.add_argument("command", nargs="*", help="Command to run in the shell.")
    return parser.parse_args()


def main():
    args = parse_args()
    single_command = shlex.join(args.command) if args.command else None
    run_shell(single_command)


if __name__ == "__main__":
    main()
