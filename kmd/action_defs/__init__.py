import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional

from cachetools import Cache, cached

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import instantiate_actions
from kmd.model.actions_model import Action
from kmd.util.format_utils import fmt_path

log = get_logger(__name__)


cache = Cache(maxsize=float("inf"))


def _import_all_files(path: Path, base_package: str, tallies: Optional[Dict[str, int]]):
    if tallies is None:
        tallies = {}

    current_package = __name__
    for _module_finder, module_name, _is_pkg in pkgutil.iter_modules(path=[str(path)]):
        importlib.import_module(f"{base_package}.{module_name}", current_package)
        tallies[base_package] = tallies.get(base_package, 0) + 1

    return tallies


def import_actions(subdir_names: List[str], tallies: Optional[Dict[str, int]] = None):
    """
    Explicit import of action definitions so all actions go into registry.
    """
    base_dir = Path(__file__).parent
    base_package = __package__

    for subdir_name in subdir_names:
        full_path = base_dir / subdir_name
        if full_path.is_dir():
            package_name = f"{base_package}.{subdir_name}"
            _import_all_files(full_path, package_name, tallies)
            log.info("Imported actions: package `%s` at %s", package_name, fmt_path(full_path))


@cached(cache)
def load_all_actions(base_only: bool = False) -> Dict[str, Action]:
    tallies: Dict[str, int] = {}
    # Allow bootstrapping base actions before compound actions that may depend on them.
    import_actions(["base_actions"], tallies)
    if not base_only:
        import_actions(["experimental_actions", "compound_actions"], tallies)

    actions_map = instantiate_actions()

    if len(actions_map) == 0:
        log.error("No actions found! Was there an import error?")

    log.info(
        "Loaded %s actions (base_only=%s): %s",
        len(actions_map),
        base_only,
        tallies,
    )

    return actions_map


def reload_all_actions(base_only: bool = False) -> Dict[str, Action]:
    cache.clear()
    return load_all_actions(base_only=base_only)


def look_up_action(action_name: str, base_only: bool = False) -> Action:
    actions = load_all_actions(base_only=base_only)
    if action_name not in actions:
        raise InvalidInput(f"Action not found: `{action_name}`")
    return actions[action_name]
