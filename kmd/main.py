"""
kmd: A command line for knowledge exploration.
"""

import atexit
import logging
import sys
from textwrap import indent
from typer import Typer
from kmd.actions.registry import load_all_actions

import kmd.config as config
from kmd.config import APP_NAME
from kmd.file_storage.file_store import locate_in_store
from kmd.tui import tui


app = Typer(help=__doc__)

app_error = None


def log_exit():
    if app_error:
        log.error("----- ! exit with error: %s", app_error)
    else:
        log.info("----- exit (success) -----")


atexit.register(log_exit)


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


if __name__ == "__main__" or __name__.endswith(".main"):
    config.setup()

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
