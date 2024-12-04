import re
from pathlib import Path
from typing import Dict, List

from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.model import (
    Action,
    ActionInput,
    ActionResult,
    ArgCount,
    ItemType,
    ONE_OR_MORE_ARGS,
    ParamList,
    Precondition,
)
from kmd.model.params_model import common_params
from kmd.preconditions.precondition_defs import is_markdown
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action
class FormatMarkdownTemplate(Action):

    name: str = "format_markdown_template"

    description: str = """
        Format the given text documents into a single document using the given
        template. The variables must be unique matching prefixes of the filename
        of each item, e.g. {body} for a file named `body.md` or `body_new_01.md`.
        """

    expected_args: ArgCount = ONE_OR_MORE_ARGS

    precondition: Precondition = is_markdown

    params: ParamList = common_params("md_template")

    md_template: Path = Path("template.md")

    def run(self, items: ActionInput) -> ActionResult:
        template_path = self.md_template

        with open(template_path, "r") as f:
            template = f.read()

        # Identify variables in the template.
        variables: List[str] = re.findall(r"\{(\w+)\}", template)

        if len(variables) != len(items):
            raise InvalidInput(
                f"Number of inputs ({len(items)} items) does not match the"
                f" number of variables ({len(variables)}) in the template"
            )

        # Create a dictionary to map variable names to item bodies.
        item_map: Dict[str, str] = {}
        unmatched_items = set(range(len(items)))

        for var in variables:
            matches = []
            for i, item in enumerate(items):
                store_path = not_none(item.store_path)
                filename = Path(store_path).stem

                if not item.body:
                    raise InvalidInput(f"Item has no body: {store_path}")

                if filename.startswith(var):
                    matches.append((i, item))

            if len(matches) == 0:
                raise InvalidInput(f"No matching item found for variable: `{var}`")
            elif len(matches) > 1:
                raise InvalidInput(
                    f"Multiple items match variable `{var}`: {[items[i].store_path for i, _ in matches]}"
                )

            index, matched_item = matches[0]
            item_map[var] = matched_item.body
            unmatched_items.remove(index)

        if unmatched_items:
            raise InvalidInput(f"Unmatched items: {[items[i].store_path for i in unmatched_items]}")

        # Format the body using the mapped items.
        body = template.format(**item_map)

        result_item = items[0].derived_copy(
            type=ItemType.doc,
            body=body,
        )

        return ActionResult([result_item])
