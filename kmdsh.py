"""
Launch xonsh with kmd extensions and customizations.
"""

import re
import warnings

from kmd.text_ui.text_styles import EMOJI_ASSISTANT

warnings.filterwarnings("ignore", category=DeprecationWarning)

from os.path import expanduser
from typing import Optional
import xonsh.main
from xonsh.main import events
from xonsh.shell import Shell
from xonsh.main import premain, postmain
from xonsh.built_ins import XSH
from xonsh.execer import Execer
from xonsh.ptk_shell.shell import PromptToolkitShell
from xonsh.readline_shell import ReadlineShell  # noqa: F401
from xonsh.xontribs import xontribs_load
from kmd.config.logger import get_logger
from kmd.text_ui.command_output import output, output_assistance

log = get_logger(__name__)

USE_CUSTOM_SHELL = True

INSTALL_TO_XONSH = False


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


def install_to_xonsh():
    """
    Script to add kmd xontrib to the .xonshrc file.
    """
    # Append the command to the file if not already present.
    if not is_xontrib_installed(xonshrc_path):
        with open(xonshrc_path, "a") as file:
            file.write(xonshrc_init_script)
        print(f"Updating your {xonshrc_path} to auto-run kmd when xonsh is invoked as kmdsh.")
    else:
        pass


def assistant_command(line: str) -> Optional[str]:
    """
    Is this a query to the assistant?
    Checks for word
    """
    line = line.strip()
    if re.search(r"\b\w+\.$", line) or re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()


# Base shell can be ReadlineShell or PromptToolkitShell.
class CustomShell(PromptToolkitShell):
    """
    Note event hooks in xonsh don't let you disable xonsh's processing, so we use a custom shell.
    """

    def default(self, line, raw_line=None):
        from kmd.assistant.assistant import assistance

        assist_query = assistant_command(line)
        if assist_query:
            try:
                output(f"{EMOJI_ASSISTANT} Getting assistance…")
                output_assistance(assistance(line))
            except Exception as e:
                log.error(f"Sorry, could not get assistance: {e}")
                log.info(e, exc_info=True)
        else:
            # Call xonsh shell.
            super().default(line)


def start_custom_xonsh(argv=None):
    # Setup for a xonsh shell, customizing just the shell itself.
    args = premain(argv)
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
    XSH.env["XONSH_INTERACTIVE"] = True  # type: ignore
    ctx["__name__"] = "__main__"
    events.on_post_init.fire()
    events.on_pre_cmdloop.fire()

    # Load kmd xontrib for rest of kmd functionality.
    xontribs_load(["kmd"])

    # Main loop.
    try:
        XSH.shell.shell.cmdloop()
    finally:
        postmain(args)


def main():
    if INSTALL_TO_XONSH:
        install_to_xonsh()

    if USE_CUSTOM_SHELL:
        start_custom_xonsh()
    else:
        # For a regular xonsh init without a customized shell:
        xonsh.main.main()


if __name__ == "__main__":
    main()
