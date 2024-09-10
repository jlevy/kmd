from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING

from kmd.model.arguments_model import StorePath

if TYPE_CHECKING:
    from kmd.model.commands_model import Command


@dataclass(frozen=True)
class CommandOutput:
    """
    Everything needed to handle and display the result of an action or command on the console.
    """

    result: Optional[Any] = None
    selection: Optional[List[StorePath]] = None
    show_result: bool = False
    show_selection: bool = False
    suggest_actions: bool = False
    display_command: Optional["Command"] = None
    exception: Optional[Exception] = None
