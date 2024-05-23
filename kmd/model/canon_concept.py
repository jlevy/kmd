from kmd.text_handling.lang_tools import capitalize_cms


def canonicalize_concept(concept: str) -> str:
    """
    Convert a concept string (general name, person, etc.) to a canonical form.
    """
    return capitalize_cms(concept)
