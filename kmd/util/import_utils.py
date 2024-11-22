import importlib
import sys
import types
from typing import Callable, List, Optional


def recursive_reload(
    package: types.ModuleType, filter_func: Optional[Callable[[str], bool]] = None
) -> List[str]:
    """
    Recursively reload all modules in the given package that match the filter function.
    Returns a list of module names that were reloaded.

    :param filter_func: A function that takes a module name and returns True if the
        module should be reloaded.
    """
    package_name = package.__name__
    modules = {
        name: module
        for name, module in sys.modules.items()
        if (
            (name == package_name or name.startswith(package_name + "."))
            and isinstance(module, types.ModuleType)
            and (filter_func is None or filter_func(name))
        )
    }
    module_names = sorted(modules.keys(), key=lambda name: name.count("."), reverse=True)
    for name in module_names:
        importlib.reload(modules[name])

    return module_names
