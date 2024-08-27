from kmd.lang_tools.capitalization import capitalize_cms


def canonicalize_concept(concept: str) -> str:
    """
    Convert a concept string (general name, person, etc.) to a canonical form.
    Drop any extraneous Markdown bullets.
    """
    return capitalize_cms(concept.strip("-* "))
