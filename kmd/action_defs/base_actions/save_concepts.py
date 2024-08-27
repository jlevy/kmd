from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
)
from kmd.model.canon_concept import canonicalize_concept
from kmd.model.errors_model import InvalidInput
from kmd.model.items_model import Item, ItemType, Format
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_markdown_list
from kmd.text_formatting.markdown_util import extract_bullet_points

log = get_logger(__name__)


@kmd_action()
class SaveConcepts(Action):
    def __init__(self):
        super().__init__(
            name="save_concepts",
            description="Creates a concept item for each value in a markdown list of concepts.",
            precondition=is_markdown_list,
        )

    def run(self, items: ActionInput) -> ActionResult:
        for item in items:
            if not item.body:
                raise InvalidInput("Item must have a body")

            concepts = extract_bullet_points(item.body)
            canon_concepts = [canonicalize_concept(concept) for concept in concepts]
            concept_items = []
            for concept in canon_concepts:
                concept_item = Item(
                    type=ItemType.concept,
                    title=concept,
                    format=Format.markdown,
                )
                concept_items.append(concept_item)

        return ActionResult(concept_items, skip_duplicates=True)
