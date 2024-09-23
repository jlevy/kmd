import json
import re

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


def fuzzy_parse_json(response: str):
    """
    Attempt to extract and parse JSON data from a string that may include spurious Markdown
    text or formatting around it.
    """

    # Remove code block markers and any markdown formatting.
    response = response.strip()
    code_block_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    match = re.search(code_block_pattern, response, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = response

    # Remove any leading or trailing text outside of JSON structures.
    json_str = json_str.strip()

    # Try to find the first '{' or '[' and the corresponding closing '}' or ']'
    try:
        # Check for JSON object.
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_substring = json_str[start : end + 1]
            return json.loads(json_substring)
        else:
            # Check for JSON array.
            start = json_str.find("[")
            end = json_str.rfind("]")
            if start != -1 and end != -1 and end > start:
                json_substring = json_str[start : end + 1]
                return json.loads(json_substring)
        # If no JSON structure found, try parsing the entire string.
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Parsing failed.
    return None
