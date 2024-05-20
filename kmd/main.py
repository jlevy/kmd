"""
kmd: A command line for knowledge exploration.
"""

import atexit
from functools import wraps
import logging
import sys
from typer import Typer
from kmd.actions.actions import run_action
from kmd.actions.registry import load_all_actions

import kmd.config as config
from kmd.config import APP_NAME
from kmd.tui import tui
from kmd.commands import commands


def _log_start():
    log.info("----- start -----")
    log.info("%s invoked: %s", APP_NAME, " ".join(sys.argv))


def _log_exit():
    if app_error:
        log.error("----- ! exit with error: %s", app_error)
    else:
        log.info("----- exit (success) -----")


# XXX: Typer breaks pytest so skip.
if not "pytest" in sys.modules:

    app = Typer(help=__doc__)

    app_error = None

    @app.command("kmd_help")
    def kmd_help():
        """
        List all available actions.
        """
        commands.kmd_help()

    def _register_commands(app: Typer):
        command_funcs = commands.all_commands()
        for func in command_funcs:
            app.command(func.__name__)(func)

        actions = load_all_actions()
        for action_name, action in actions.items():

            def dynamic_command(action_name, action):
                def command(locator: str):
                    run_action(action_name, locator)

                command.__doc__ = f"Action: {action.description}"
                return command

            app.command(action_name)(dynamic_command(action_name, action))

    @app.command()
    def ui():
        """
        Run the text-based user interface.
        """
        tui.run()

    if __name__ == "__main__" or __name__.endswith(".main"):
        config.setup()

        atexit.register(_log_exit)

        log = logging.getLogger(__name__)
        _log_start()

        if isinstance(app, Typer):
            _register_commands(app)

        if len(sys.argv) == 1:
            app(prog_name=APP_NAME, args=["--help"])
        else:
            try:
                app()
            except Exception as e:
                app_error = e
                raise
