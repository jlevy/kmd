"""
kmd: A command line for knowledge exploration.
"""

import atexit
import sys
from typer import Typer
from kmd.action_exec.action_exec import run_action
from kmd.action_defs import load_all_actions
from kmd.config.setup import setup
from kmd.config.settings import APP_NAME
from kmd.commands import commands
from kmd.config.logger import get_logger


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

    if __name__ == "__main__" or __name__.endswith(".main"):
        setup()

        atexit.register(_log_exit)

        log = get_logger(__name__)
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
