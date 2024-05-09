from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from kmd.model.items_model import Item


# For now these are simple but we will want to support other hints or output data in the future.
ActionInput = List[Item]
ActionResult = List[Item]


@dataclass
class Action:
    name: str
    friendly_name: str
    description: str
    implementation: str = "builtin"
    model: Optional[str] = None
    title_template: Optional[str] = None
    template: Optional[str] = None
    system_message: Optional[str] = None

    @abstractmethod
    def run(self, items: ActionInput) -> ActionResult:
        pass
