"""
Script to add kmd xontrib to the .xonshrc file.
"""

from os.path import expanduser


def install():
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
            file.write("\n# Auto-install of kmd:\n")
            file.write(xontrib_command)
        print(f"Added kmd xontrib to load in xonsh automatically in {xonshrc_path}")
    else:
        print(f"kmd xontrib is already set up to load in {xonshrc_path}")


if __name__ == "__main__":
    install()
