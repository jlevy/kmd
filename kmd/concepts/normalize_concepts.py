from kmd.model.canon_concept import canonicalize_concept
from kmd.text_formatting.markdown_util import as_bullet_points, extract_bullet_points


def normalize_concepts_list(markdown_text: str) -> str:
    """
    Normalize, capitalize, sort, and then remove exact duplicates from a Markdown
    list of concepts.
    """
    concepts = extract_bullet_points(markdown_text)
    normalized_concepts = sorted(set(canonicalize_concept(concept) for concept in concepts))
    return as_bullet_points(normalized_concepts)
