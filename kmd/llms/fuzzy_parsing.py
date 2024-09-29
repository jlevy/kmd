import json
import re
from textwrap import dedent

from thefuzz import fuzz


NO_RESULTS = "(No results)"


def is_no_results(response: str) -> bool:
    return fuzzy_match(response, "") or fuzzy_match(response, NO_RESULTS)


def fuzzy_match(response: str, sentinel: str, threshold: int = 80) -> bool:
    """
    Check if the response contains a sentinel value.
    """
    response = response.lower().strip()
    sentinel = sentinel.lower().strip()
    return bool(response and fuzz.ratio(response, sentinel) > threshold)


def strip_markdown_fence(response: str) -> str:
    """
    Remove any extraneous Markdown fenced code block markers wrapping a response.
    """
    response = response.strip()
    code_block_pattern = r"^```(?:\w+)?\s*\n(.*?)\n```\s*$"
    match = re.match(code_block_pattern, response, re.DOTALL)
    if match:
        response = match.group(1).strip()
    return response.strip()


def fuzzy_parse_json(response: str):
    """
    Attempt to parse JSON data from a string, after removing any markdown code blocks.
    """
    json_str = strip_markdown_fence(response)

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

    return None


## Tests


def test_fuzzy_parsing():
    response = dedent(
        """
        ```markdown
        This is a test.
        ```
        """
    )
    assert strip_markdown_fence(response) == "This is a test."

    response = """
    ```json
    {
        "key": "value"
    }
    """
    expected = {"key": "value"}
    assert fuzzy_parse_json(response) == expected

    response = '{ "key": "value" }'
    expected = {"key": "value"}
    assert fuzzy_parse_json(response) == expected

    response = "This is not JSON."
    assert fuzzy_parse_json(response) is None
