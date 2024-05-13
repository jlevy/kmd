"""
kmd: A command line for knowledge exploration.
"""

import atexit
from functools import wraps
import logging
import sys
from textwrap import indent
from typing import List, Tuple
import typer
from typer import Typer
from typing_extensions import Annotated
from kmd.actions.actions import run_action
from kmd.actions.registry import load_all_actions

import kmd.config as config
from kmd.config import APP_NAME
from kmd.tui import tui
from kmd.commands import commands

_is_pytest = "pytest" in sys.modules


# XXX Dumb hack to avoid pytest errors with Typer.
class _DummyTyper:
    def __call__(self, *args, **kwargs):
        pass

    def command(self, *args, **kwargs):
        return wraps


app = Typer(help=__doc__) if not _is_pytest else _DummyTyper()


app_error = None


def log_exit():
    if app_error:
        log.error("----- ! exit with error: %s", app_error)
    else:
        log.info("----- exit (success) -----")


@app.command("list_actions")
def list_actions():
    """
    List all available actions.
    """

    commands.list_actions()


def _complete_action_names(incomplete: str) -> List[Tuple[str, str]]:
    actions = load_all_actions()
    return [
        (action.name, action.friendly_name)
        for action in actions.values()
        if action.name.startswith(incomplete)
    ]


@app.command()
def action(
    action_name: Annotated[str, typer.Argument(autocompletion=_complete_action_names)],
    locator: str,
):
    """
    Perform an action on the given item.
    """

    # TODO: Handle multiple input items.
    run_action(action_name, locator)


@app.command()
def ui():
    """
    Run the text-based user interface.
    """
    tui.run()


if (__name__ == "__main__" or __name__.endswith(".main")) and not _is_pytest:
    config.setup()

    atexit.register(log_exit)

    log = logging.getLogger(__name__)
    log.info("----- start -----")
    log.info("%s invoked: %s", APP_NAME, " ".join(sys.argv))

    if len(sys.argv) == 1:
        app(prog_name=APP_NAME, args=["--help"])
    else:
        try:
            app()
        except Exception as e:
            app_error = e
            raise
