"""
Launch xonsh with kmd extensions auto-loaded.
"""

import sys
from os.path import expanduser
from xonsh.main import main as xonsh_main


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


def main():
    install_to_xonsh()

    sys.exit(xonsh_main())


if __name__ == "__main__":
    main()
