"""
A variety of configs and customizations for xonsh to work as the kmd shell.
"""

import os
import time
from os.path import expanduser
from typing import List, Optional, override

from pygments.token import Token
from xonsh.built_ins import XSH
from xonsh.environ import xonshrc_context
from xonsh.execer import Execer
from xonsh.main import events
from xonsh.shell import Shell
from xonsh.xontribs import xontribs_load

# Keeping initial imports/deps minimal.
from kmd.config.lazy_imports import import_start_time
from kmd.config.logger import get_console, get_logger
from kmd.config.settings import APP_NAME, find_rcfiles
from kmd.config.text_styles import PROMPT_INPUT_COLOR, SPINNER
from kmd.shell.shell_output import cprint
from kmd.shell.shell_syntax import is_assist_request_str


log = get_logger(__name__)


# Turn off for cleaner outputs. Sometimes you want this on for development.
XONSH_SHOW_TRACEBACK = False


## -- Non-customized xonsh shell setup --

xonshrc_init_script = """
# Auto-load of kmd:
# This only activates if xonsh is invoked as kmd.
xontrib load -f kmd.xontrib.kmd_extension
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


## -- Custom xonsh shell setup --


# Base shell can be ReadlineShell or PromptToolkitShell.
# Completer can be RankingCompleter or the standard Completer.
# from xonsh.completer import Completer
# from xonsh.shells.readline_shell import ReadlineShell
from xonsh.shells.ptk_shell import PromptToolkitShell

from kmd.xonsh_customization.xonsh_ranking_completer import RankingCompleter


class CustomAssistantShell(PromptToolkitShell):
    """
    Our custom version of the interactive xonsh shell.

    Note event hooks in xonsh don't let you disable xonsh's processing, so we use a custom shell.
    """

    def __init__(self, **kwargs):
        from xonsh.shells.ptk_shell.completer import PromptToolkitCompleter

        # Set the completer to our custom one.
        # XXX Need to disable the default Completer, then overwrite with our custom one.
        super().__init__(completer=False, **kwargs)
        self.completer = RankingCompleter()
        self.pt_completer = PromptToolkitCompleter(self.completer, self.ctx, self)

        # TODO: Consider patching in additional keybindings e.g. for custom mouse support.
        # self.key_bindings = merge_key_bindings([custom_ptk_keybindings(), self.key_bindings])

        log.info(
            "CustomAssistantShell: initialized completer=%s, pt_completer=%s",
            self.completer,
            self.pt_completer,
        )

    def default(self, line, raw_line=None):
        from kmd.help.assistant import shell_context_assistance

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


# XXX xonsh's Shell class hard-codes available shell types, but does have some
# helpful scaffolding, so let's override to use ours.
class CustomShell(Shell):
    @override
    @staticmethod
    def construct_shell_cls(backend, **kwargs):
        log.info("Using %s: %s", CustomAssistantShell.__name__, kwargs)
        return CustomAssistantShell(**kwargs)


@events.on_command_not_found
def not_found(cmd: List[str]):
    from kmd.help.assistant import shell_context_assistance

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
        # Auto-cd if a directory name is typed.
        "AUTO_CD": True,
        # Having this true makes processes hard to interrupt with Ctrl-C.
        # https://xon.sh/envvars.html#thread-subprocs
        "THREAD_SUBPROCS": False,
        "XONSH_INTERACTIVE": is_interactive,
        "XONSH_SHOW_TRACEBACK": XONSH_SHOW_TRACEBACK,
        # TODO: Consider enabling and adapting auto-suggestions.
        "AUTO_SUGGEST": False,
        # Completions can be "none", "single", "multi", or "readline".
        # "single" lets us have rich completions with descriptions alongside.
        # https://xon.sh/envvars.html#completions-display
        "COMPLETIONS_DISPLAY": "single",
        # Number of rows in the fancier prompt toolkit completion menu.
        "COMPLETIONS_MENU_ROWS": 8,
        # Mode is "default" (fills in common prefix) or "menu-complete" (fills in first match).
        "COMPLETION_MODE": "default",
        # If true, show completions always, after each keypress.
        # TODO: Find a way to do this after a delay. Instantly showing this is annoying.
        "UPDATE_COMPLETIONS_ON_KEYPRESS": False,
        # Mouse support for completions by default interferes with other mouse scrolling.
        # TODO: Enable mouse support but disable scroll events.
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


def load_rcfiles(execer: Execer, ctx: dict):
    rcfiles = [str(f) for f in find_rcfiles()]
    if rcfiles:
        log.info("Loading rcfiles: %s", rcfiles)
        xonshrc_context(rcfiles=rcfiles, execer=execer, ctx=ctx, env=XSH.env, login=True)


def start_custom_xonsh(single_command: Optional[str] = None):
    """
    Customize xonsh shell, with custom shell settings and input loop hooks as well
    as the kmd xontrib that loads kmd commands.
    """
    import builtins

    # XXX: A hack to get kmd help to replace Python help. We just delete the builtin help so
    # that kmd's help can be used in its place (otherwise builtins override aliases).
    del builtins.help

    # Make process title "kmd" instead of "xonsh".
    try:
        from setproctitle import setproctitle

        setproctitle(APP_NAME)
    except ImportError:
        pass

    # Seems like we have to do our own setup as premain/postmain can't be customized.
    ctx = {}
    execer = Execer(
        filename="<stdin>",
        debug_level=0,
        scriptcache=True,
        cacheall=False,
    )
    XSH.load(ctx=ctx, execer=execer, inherit_env=True)
    XSH.shell = CustomShell(execer=execer, ctx=ctx)  # type: ignore

    is_interactive = False if single_command else True

    customize_xonsh_settings(is_interactive)

    ctx["__name__"] = "__main__"
    events.on_post_init.fire()
    events.on_pre_cmdloop.fire()

    # Load kmd xontrib for rest of kmd functionality.
    xontribs_load(["kmd.xontrib.kmd_extension"], full_module=True)

    # If we want to replicate all the xonsh settings including .xonshrc, we could call
    # start_services(). It may be problematic to support all xonsh enhancements, however,
    # so let's only load ~/.kmdrc files.
    load_rcfiles(execer, ctx)

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
        XSH.unload()
        XSH.shell = None
