"""
Run xonsh with kmd extensions auto-loaded.
"""

import sys
from os.path import expanduser
from xonsh.main import main as xonsh_main


def install_to_xonsh():
    """
    Script to add kmd xontrib to the .xonshrc file.
    """

    xontrib_command = "xontrib load kmd\n"

    xonshrc_path = expanduser("~/.xonshrc")

    def is_xontrib_installed(file_path, command):
        try:
            with open(file_path, "r") as file:
                for line in file:
                    if command.strip() == line.strip():
                        return True
        except FileNotFoundError:
            return False
        return False

    # Append the command to the file if not already present.
    if not is_xontrib_installed(xonshrc_path, xontrib_command):
        with open(xonshrc_path, "a") as file:
            file.write("\n# Auto-load of kmd:\n")
            file.write(xontrib_command)
        print(f"Added kmd xontrib to load in xonsh automatically in {xonshrc_path}")
    else:
        pass


def main():
    install_to_xonsh()

    sys.exit(xonsh_main())


if __name__ == "__main__":
    main()
