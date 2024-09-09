from kmd.concepts.embeddings import Embeddings
from kmd.concepts.text_similarity import find_related_pairs, relate_texts_by_embedding
from kmd.exec.action_registry import kmd_action
from kmd.lang_tools.inflection import lemmatized_equal
from kmd.model import (
    TWO_OR_MORE_ARGS,
    Action,
    ActionInput,
    ActionResult,
    PathOp,
    PathOpType,
    StorePath,
)
from kmd.config.logger import get_logger
from kmd.preconditions.precondition_defs import is_concept, is_text_doc
from kmd.text_formatting.markdown_util import as_bullet_points
from kmd.text_ui.command_output import output, output_heading
from kmd.util.type_utils import not_none

log = get_logger(__name__)


@kmd_action()
class FindNearDuplicates(Action):
    def __init__(self):
        super().__init__(
            name="find_near_duplicates",
            description="""
                Look at input items and find near duplicate items using text embeddings, based on title or body.
                """,
            expected_args=TWO_OR_MORE_ARGS,
            precondition=is_concept | is_text_doc,
        )

    def run(self, items: ActionInput) -> ActionResult:
        keyvals = [(not_none(item.store_path), item.full_text()) for item in items]
        item_map = {item.store_path: item for item in items}

        report_threshold = 0.6
        archive_threshold = 0.9

        embeddings = Embeddings.embed(keyvals)
        relatedness_matrix = relate_texts_by_embedding(embeddings)
        near_duplicates = find_related_pairs(relatedness_matrix, threshold=report_threshold)

        # Give a report on most related items.
        report_lines = []
        duplicate_paths = []
        for key1, key2, score in near_duplicates:
            item1 = item_map[key1]
            item2 = item_map[key2]
            lem_eq = lemmatized_equal(item1.full_text(), item2.full_text())
            line = f"{item1.title} <-> {item2.title} ({score:.3f}) {lem_eq}"
            report_lines.append(line)

            if score >= archive_threshold or lem_eq:
                duplicate_paths.append(key1)  # key1 will be the shorter one.
        report = as_bullet_points(report_lines)

        output_heading("Near Duplicates")
        output(f"Most-related items (score >= {report_threshold}):")
        output()
        output("%s", report)
        output()

        # TODO: Handle concepts that subsume other concepts, e.g. find ones like this even
        # though the similarity score is low:
        # - AGI <-> AGI (Artificial General Intelligence) (0.640)

        return ActionResult(
            [],
            path_ops=[
                PathOp(store_path=StorePath(path), op=PathOpType.select) for path in duplicate_paths
            ],
        )
