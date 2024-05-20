import sys
from kmd.config.setup import setup
from kmd.tui.workspace_browser import WorkspaceBrowser


def run():
    WorkspaceBrowser().run()


if __name__ == "__main__" and not "pytest" in sys.modules:
    setup()
    run()
