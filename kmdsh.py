"""
Run xonsh with kmd extensions auto-loaded.
"""

import sys
from os.path import expanduser
from xonsh.main import main as xonsh_main


xontrib_command = "xontrib load kmd"

xonshrc_init_script = """
# Auto-load of kmd and kmd prompt setup:
xontrib load kmd

def _xonsh_prompt():
   from kmd.file_storage.workspaces import current_workspace_name
   name = current_workspace_name()
   workspace_str = "{BOLD_GREEN}" + name if name else "{BOLD_YELLOW}(no workspace)"
   return '%s {BOLD_GREEN}❯{RESET} ' % workspace_str
   
$PROMPT = _xonsh_prompt
# End of kmd setup.
"""

xonshrc_path = expanduser("~/.xonshrc")


def is_xontrib_installed(file_path):
    try:
        with open(file_path, "r") as file:
            for line in file:
                if xontrib_command.strip() == line.strip():
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
        print(f"Added kmd xontrib to load in xonsh automatically in {xonshrc_path}")
    else:
        pass


def main():
    install_to_xonsh()

    sys.exit(xonsh_main())


if __name__ == "__main__":
    main()
