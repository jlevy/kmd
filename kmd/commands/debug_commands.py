from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.server.local_server import restart_server
from kmd.shell_ui.kyrm_codes import IframePopover, TextTooltip

log = get_logger(__name__)


@kmd_command
def reload_kmd() -> None:
    """
    Reload the kmd package and all its submodules. Also restarts the local the
    local server.

    Not perfect! But sometimes useful for development.
    """
    import kmd
    from kmd.util.import_utils import recursive_reload

    module = kmd
    exclude = ["kmd.xontrib.kmd_extension"]  # Don't reload the kmd initialization.

    def filter_func(name: str) -> bool:
        if exclude:
            for excluded_module in exclude:
                if name == excluded_module or name.startswith(excluded_module + "."):
                    log.info("Excluding reloading module: %s", name)
                    return False
        return True

    package_names = recursive_reload(module, filter_func=filter_func)
    log.info("Reloaded modules: %s", ", ".join(package_names))
    log.message("Reloaded %s modules from %s.", len(package_names), module.__name__)

    restart_server()

    # TODO Re-register commands and actions.


@kmd_command
def kyrm_text_tooltip(text: str) -> None:
    """
    Show a tooltip in the Kyrm terminal.
    """
    tooltip = TextTooltip(text=text)
    print(tooltip.as_osc(), end="")


@kmd_command
def kyrm_iframe_popover(url: str) -> None:
    """
    Show an iframe popover in the Kyrm terminal.
    """
    popover = IframePopover(url=url)
    print(popover.as_osc(), end="")
