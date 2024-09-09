from typing import List

from kmd.model.canon_concept import canonicalize_concept
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemType
from kmd.text_formatting.markdown_util import extract_bullet_points


def normalize_concepts(concepts: List[str]) -> List[str]:
    return sorted(set(canonicalize_concept(concept) for concept in concepts))


def concepts_from_markdown(markdown_text: str) -> List[str]:
    """
    Parse, normalize, capitalize, sort, and then remove exact duplicates from a Markdown
    list of concepts.
    """
    concepts = extract_bullet_points(markdown_text)
    return normalize_concepts(concepts)


def as_concept_items(concepts: List[str]) -> List[Item]:
    concept_items = []
    for concept in concepts:
        concept_item = Item(
            type=ItemType.concept,
            title=concept,
            format=Format.markdown,
        )
        concept_items.append(concept_item)
    return concept_items
