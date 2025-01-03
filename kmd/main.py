"""
Main entry point for kmd shell.
Uses customized xonsh shell.
"""

import sys
from contextlib import redirect_stdout
from io import StringIO
from typing import Optional

import xonsh.main

# Keeping initial imports/deps minimal.
from kmd.config.logger import get_logger
from kmd.config.settings import APP_NAME
from kmd.config.setup import setup
from kmd.version import get_version
from kmd.xonsh_shell import install_to_xonshrc, start_custom_xonsh


# Ensure logging is set up before anything else.
setup()

log = get_logger(__name__)

__version__ = get_version()

APP_VERSION = f"{APP_NAME} {__version__}"

# If true use the kmd-customized xonsh shell. This is now the recommended way to run kmd since
# it then supports custom parsing of shell input to include LLM-based assistance, etc.
# Alternatively, we can run a regular xonsh shell and have it load kmd commands via the
# xontrib only (in ~/.xonshrc) but this is not preferred.
USE_KMD_SHELL = True


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


def parse_args() -> Optional[str]:
    # Do our own arg parsing since everything except these two options
    # should be handled as a kmd command.
    if sys.argv[1:] == ["--version"]:
        print(APP_VERSION)
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
