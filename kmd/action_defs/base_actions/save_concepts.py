from kmd.concepts.concept_formats import (
    as_concept_items,
    concepts_from_markdown,
    normalize_concepts,
)
from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import Action, ActionInput, ActionResult, ArgCount, ONE_OR_MORE_ARGS, Precondition
from kmd.preconditions.precondition_defs import is_markdown_list

log = get_logger(__name__)


@kmd_action
class SaveConcepts(Action):

    name: str = "save_concepts"

    description: str = """
        Creates a concept item for each value in a markdown list of concepts.
        Skips existing concepts and duplicates.
        """

    expected_args: ArgCount = ONE_OR_MORE_ARGS

    precondition: Precondition = is_markdown_list

    def run(self, items: ActionInput) -> ActionResult:
        concepts = []
        for item in items:
            if not item.body:
                raise InvalidInput("Item must have a body")

            concepts.extend(concepts_from_markdown(item.body))

        result_items = as_concept_items(normalize_concepts(concepts))

        return ActionResult(result_items, skip_duplicates=True)
