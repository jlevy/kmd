"""
Xonsh extension for kmd.

Sets up all commands and actions for use in xonsh. This makes using kmd far easier
for interactive use than from a regular shell command line.

Can run from the custom kmd shell (main.py) or from a regular xonsh shell.
"""

import importlib
import os
import runpy

from kmd.action_defs import reload_all_actions
from kmd.commands.command_registry import kmd_command
from kmd.text_formatting.text_formatting import fmt_path
from kmd.text_ui.command_output import output
from kmd.xontrib.xonsh_customization import _load_xonsh_actions, customize_xonsh, set_alias

# FIXME: Only use absolute imports here.


# We add action loading here directly in the xontrib so we expose `load` and
# can update the aliases.
@kmd_command
def load(*paths: str) -> None:
    """
    Load kmd Python extensions. Simply imports and the defined actions should use
    @kmd_action() to register themselves.
    """
    for path in paths:
        if os.path.isfile(path) and path.endswith(".py"):
            runpy.run_path(path, run_name="__main__")
        else:
            importlib.import_module(path)

    # Now reload all actions into the environment so the new action is visible.
    reload_all_actions()
    _load_xonsh_actions()

    output("Imported extensions and reloaded actions: %s", ", ".join(fmt_path(p) for p in paths))
    # TODO: Track and expose to the user which extensions are loaded.


set_alias("load", load)

customize_xonsh()
