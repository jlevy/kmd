import re
from typing import Optional

from kmd.util.parse_shell_args import shell_quote


def is_assist_request_str(line: str) -> Optional[str]:
    """
    Is this a query to the assistant?
    Checks for phrases ending in a ? or a period, or starting with a ?.
    """
    line = line.strip()
    if re.search(r"\b\w+\.$", line) or re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()
    return None


def assist_request_str(request: str) -> str:
    """
    Command string to call the assistant.
    """
    return f"? {shell_quote(request, idempotent=True)}"
