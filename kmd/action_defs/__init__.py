import importlib


def import_all_actions():
    """Explicit import so all actions go into registry."""
    modules = ["export_actions", "llm_actions", "media_actions"]

    for module in modules:
        importlib.import_module("." + module, __name__)
