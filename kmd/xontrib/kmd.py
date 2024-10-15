"""
Xonsh extension for kmd.

These are the additions to xonsh that don't involve customizing the shell itself.

Sets up all commands and actions for use in xonsh.

Can run from the custom kmd shell (main.py) or from a regular xonsh shell.
"""

# Using absolute imports to avoid polluting the user's shell namespace.
import kmd.action_defs
import kmd.commands.command_registry
import kmd.text_ui.command_output
import kmd.util.format_utils
import kmd.xontrib.xonsh_customization


# We add action loading here directly in the xontrib so we expose `load` and
# can update the aliases.
@kmd.commands.command_registry.kmd_command
def load(*paths: str) -> None:
    """
    Load kmd Python extensions. Simply imports and the defined actions should use
    @kmd_action to register themselves.
    """
    import importlib
    import os
    import runpy

    for path in paths:
        if os.path.isfile(path) and path.endswith(".py"):
            runpy.run_path(path, run_name="__main__")
        else:
            importlib.import_module(path)

    # Now reload all actions into the environment so the new action is visible.
    kmd.action_defs.reload_all_actions()
    kmd.xontrib.xonsh_customization._load_xonsh_actions()

    kmd.text_ui.command_output.output(
        "Imported extensions and reloaded actions: %s",
        ", ".join(kmd.util.format_utils.fmt_path(p) for p in paths),
    )
    # TODO: Track and expose to the user which extensions are loaded.


kmd.xontrib.xonsh_customization.set_alias("load", load)

kmd.xontrib.xonsh_customization.customize_xonsh()
