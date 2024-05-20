import sys
from kmd import config
from kmd.tui.workspace_browser import WorkspaceBrowser


def run():
    WorkspaceBrowser().run()


if __name__ == "__main__" and not "pytest" in sys.modules:
    config.setup()
    run()
