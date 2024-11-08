"""
Launch xonsh with kmd extensions and customizations.
"""

import os
import sys
import time
from contextlib import redirect_stdout
from io import StringIO
from os.path import expanduser
from typing import List, Optional

import xonsh.main
from pygments.token import Token
from xonsh.built_ins import XSH
from xonsh.execer import Execer
from xonsh.main import events, postmain, premain
from xonsh.shell import Shell
from xonsh.xontribs import xontribs_load

from kmd.config.lazy_imports import import_start_time
from kmd.config.logger import get_console, get_logger
from kmd.config.settings import APP_NAME
from kmd.config.setup import setup
from kmd.config.text_styles import PROMPT_INPUT_COLOR, SPINNER
from kmd.help.assistant import shell_context_assistance
from kmd.model.commands_model import is_assist_request_str
from kmd.shell.shell_output import cprint
from kmd.version import get_version


# Ensure logging is set up before anything else.
setup()

log = get_logger(__name__)

__version__ = get_version()

# If true use the kmd-customized xonsh shell. This is now the recommended way to run kmd since
# it then supports custom parsing of shell input to include LLM-based assistance, etc.
# Alternatively, we can run a regular xonsh shell and have it load kmd commands via the
# xontrib only (in ~/.xonshrc) but this is not preferred.
USE_KMD_SHELL = True

# Turn off for cleaner outputs. Sometimes you want this on for development.
XONSH_SHOW_TRACEBACK = True


## Non-customized xonsh shell setup

xonshrc_init_script = """
# Auto-load of kmd:
# This only activates if xonsh is invoked as kmd.
xontrib load -f kmd.xontrib.kmd
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


## Custom xonsh shell setup

# Base shell can be ReadlineShell or PromptToolkitShell.
# from xonsh.shells.readline_shell import ReadlineShell
from xonsh.shells.ptk_shell import PromptToolkitShell


class CustomInteractiveShell(PromptToolkitShell):  # PromptToolkitShell or ReadlineShell
    """
    Our custom version of the interactive xonsh shell.

    Note event hooks in xonsh don't let you disable xonsh's processing, so we use a custom shell.
    """

    def default(self, line, raw_line=None):
        assist_query = is_assist_request_str(line)
        if assist_query:
            try:
                with get_console().status("Thinking…", spinner=SPINNER):
                    shell_context_assistance(assist_query)
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
        cprint("Command not found. Getting assistance…")
        with get_console().status("", spinner=SPINNER):
            shell_context_assistance(
                f"""
                The user just typed the following command, but it was not found:

                {" ".join(cmd)}

                Please give them a brief suggestion of possible correct commands
                and how they can get more help with `help` or any question
                ending with ? in the terminal.
                """,
                fast=True,
            )


def customize_xonsh_settings(is_interactive: bool):
    """
    Xonsh settings to customize xonsh better kmd usage.
    """

    default_settings = {
        # Having this true makes processes hard to interrupt with Ctrl-C.
        # https://xon.sh/envvars.html#thread-subprocs
        "THREAD_SUBPROCS": False,
        "XONSH_INTERACTIVE": is_interactive,
        "XONSH_SHOW_TRACEBACK": XONSH_SHOW_TRACEBACK,
        "AUTO_SUGGEST": False,
        # Completions can be "none", "single", "multi", or "readline".
        # https://xon.sh/envvars.html#completions-display
        "COMPLETIONS_DISPLAY": "single",
        # Number of rows in the fancier prompt toolkit completion menu.
        "COMPLETIONS_MENU_ROWS": 8,
        # Mode is "default" or "menu-complete".
        "COMPLETION_MODE": "menu-complete",
        # Mouse support for completions should be off since it interferes with other mouse scrolling.
        "MOUSE_SUPPORT": False,
        # Start with default colors then override prompt toolkit colors
        # being the same input color.
        "XONSH_COLOR_STYLE": "default",
        "XONSH_STYLE_OVERRIDES": {
            Token.Text: PROMPT_INPUT_COLOR,
            Token.Keyword: PROMPT_INPUT_COLOR,
            Token.Name: PROMPT_INPUT_COLOR,
            Token.Name.Builtin: PROMPT_INPUT_COLOR,
            Token.Name.Variable: PROMPT_INPUT_COLOR,
            Token.Name.Variable.Magic: PROMPT_INPUT_COLOR,
            Token.Name.Variable.Instance: PROMPT_INPUT_COLOR,
            Token.Name.Variable.Class: PROMPT_INPUT_COLOR,
            Token.Name.Variable.Global: PROMPT_INPUT_COLOR,
            Token.Name.Function: PROMPT_INPUT_COLOR,
            Token.Name.Constant: PROMPT_INPUT_COLOR,
            Token.Name.Namespace: PROMPT_INPUT_COLOR,
            Token.Name.Class: PROMPT_INPUT_COLOR,
            Token.Name.Decorator: PROMPT_INPUT_COLOR,
            Token.Name.Exception: PROMPT_INPUT_COLOR,
            Token.Name.Tag: PROMPT_INPUT_COLOR,
            Token.Keyword.Constant: PROMPT_INPUT_COLOR,
            Token.Keyword.Namespace: PROMPT_INPUT_COLOR,
            Token.Keyword.Type: PROMPT_INPUT_COLOR,
            Token.Keyword.Declaration: PROMPT_INPUT_COLOR,
            Token.Keyword.Reserved: PROMPT_INPUT_COLOR,
            Token.Punctuation: PROMPT_INPUT_COLOR,
            Token.String: PROMPT_INPUT_COLOR,
            Token.Number: PROMPT_INPUT_COLOR,
            Token.Generic: PROMPT_INPUT_COLOR,
            Token.Operator: PROMPT_INPUT_COLOR,
            Token.Operator.Word: PROMPT_INPUT_COLOR,
            Token.Other: PROMPT_INPUT_COLOR,
            Token.Literal: PROMPT_INPUT_COLOR,
            Token.Comment: PROMPT_INPUT_COLOR,
            Token.Comment.Single: PROMPT_INPUT_COLOR,
            Token.Comment.Multiline: PROMPT_INPUT_COLOR,
            Token.Comment.Special: PROMPT_INPUT_COLOR,
        },
    }

    # Apply settings, unless environment variables are already set otherwise.
    for key, default_value in default_settings.items():
        XSH.env[key] = os.environ.get(key, default_value)  # type: ignore


def start_custom_xonsh(single_command: Optional[str] = None):
    """
    Customize xonsh shell, with custom shell settings and input loop hooks as well
    as the kmd xontrib that loads kmd commands.
    """
    import builtins

    # XXX: A hack to get kmd help to replace Python help. We just delete the builtin help so
    # that kmd's help can be used in its place (otherwise builtins override aliases).
    del builtins.help

    args = premain(None)  # No xonsh args.

    # Make process title "kmd" instead of "xonsh".
    try:
        from setproctitle import setproctitle as spt

        spt(APP_NAME)
    except ImportError:
        pass

    ctx = {}
    execer = Execer(
        filename="<stdin>",
        debug_level=0,
        scriptcache=True,
        cacheall=False,
    )
    XSH.load(ctx=ctx, execer=execer, inherit_env=True)
    XSH.shell = Shell(execer=execer)  # type: ignore
    XSH.shell.shell = CustomInteractiveShell(execer=execer, ctx=ctx)  # type: ignore

    is_interactive = False if single_command else True

    customize_xonsh_settings(is_interactive)

    ctx["__name__"] = "__main__"
    events.on_post_init.fire()
    events.on_pre_cmdloop.fire()

    # Load kmd xontrib for rest of kmd functionality.
    xontribs_load(["kmd.xontrib.kmd"], full_module=True)

    # Imports are so slow we will need to improve this. Let's time it.
    startup_time = time.time() - import_start_time
    log.info(f"kmd startup took {startup_time:.2f}s.")

    # Main loop.
    try:
        if single_command:
            # Run a command.
            XSH.shell.shell.default(single_command)  # type: ignore
        else:
            XSH.shell.shell.cmdloop()  # type: ignore
    finally:
        postmain(args)


def run_shell(single_command: Optional[str] = None):
    if USE_KMD_SHELL:
        start_custom_xonsh(single_command)
    else:
        # For a traditional xonsh init without a customized shell.
        # This isn't recommended since some features aren't available.
        # When running in regular xonsh we need to load kmd xontrib via xonshrc.
        install_to_xonshrc()
        xonsh.main.main()


def print_help():
    from kmd.commands import help_commands

    output = StringIO()
    with redirect_stdout(output):
        help_commands.help()
    print(output.getvalue())


def parse_args():
    # Do our own arg parsing since everything except these two options
    # should be handled as a kmd command.
    if sys.argv[1:] == ["--version"]:
        print(f"{sys.argv[0]} {__version__}")
        sys.exit(0)
    elif sys.argv[1:] == ["--help"]:
        print_help()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1].startswith("-"):
        print(f"Unrecognized option: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)

    # Everything else is a kmd command so passed to the shell.
    return " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None


def main():
    command = parse_args()
    run_shell(command)


if __name__ == "__main__":
    main()
