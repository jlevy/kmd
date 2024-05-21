import importlib

MODULES = [
    "export_actions",
    "llm_actions",
    "media_actions",
]


def import_all_actions():
    """
    Explicit import so all actions go into registry.
    """
    for module in MODULES:
        importlib.import_module("." + module, __name__)
