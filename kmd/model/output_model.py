from typing import Any, List, Optional

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from kmd.model.commands_model import Command
from kmd.model.paths_model import StorePath


@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
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
