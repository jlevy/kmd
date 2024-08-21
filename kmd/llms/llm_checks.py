from thefuzz import fuzz


def fuzzy_match(response: str, sentinel: str) -> bool:
    """
    Check if the response contains a sentinel value.
    """
    response = response.lower().strip()
    sentinel = sentinel.lower().strip()
    return fuzz.ratio(response, sentinel) > 80 or not response
