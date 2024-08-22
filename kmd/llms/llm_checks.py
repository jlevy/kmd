from thefuzz import fuzz


NO_RESULTS = "(No results)"


def is_no_results(response: str) -> bool:
    return fuzzy_match(response, NO_RESULTS)


def fuzzy_match(response: str, sentinel: str, threshold: int = 80) -> bool:
    """
    Check if the response contains a sentinel value.
    """
    response = response.lower().strip()
    sentinel = sentinel.lower().strip()
    return fuzz.ratio(response, sentinel) > threshold or not response
