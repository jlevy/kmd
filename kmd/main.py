"""
kmd: A command line for knowledge exploration.
"""

import atexit
from functools import wraps
import logging
import sys
from textwrap import indent
from typer import Typer
from kmd.actions.registry import load_all_actions

import kmd.config as config
from kmd.config import APP_NAME
from kmd.file_storage.file_store import locate_in_store
from kmd.tui import tui

# XXX Dumb hack to avoid pytest errors with Typer.
_is_pytest = 'pytest' in sys.modules
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




@app.command()
def list_actions():
    """
    List all available actions.
    """

    actions = load_all_actions()
    for action in actions.values():
        print(f"{action.name} - {action.friendly_name}:\n{indent(action.description, prefix="    ")}\n")


@app.command()
def action(action_name: str, locator: str):
    """
    Perform an action on the given item.
    """

    actions = load_all_actions()
    action = actions[action_name]

    item = locate_in_store(locator)

    # TODO: Handle multiple input items.
    action.run([item])


@app.command()
def ui():
    """
    Run the text-based user interface.
    """
    tui.run()


if __name__ == "__main__" or __name__.endswith(".main") and not _is_pytest:
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
