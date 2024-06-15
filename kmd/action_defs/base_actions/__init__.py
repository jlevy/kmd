import importlib
import pkgutil


def import_base_actions():
    """
    Explicit import so all actions go into registry.
    """
    current_package = __name__
    for _, module_name, _ in pkgutil.iter_modules(path=__path__):
        importlib.import_module(f".{module_name}", current_package)
