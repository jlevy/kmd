from textwrap import indent
from typing import Dict, List

import litellm
from slugify import slugify
from strif import abbreviate_str

from kmd.config.logger import get_logger
from kmd.config.settings import LogLevel
from kmd.config.text_styles import HRULE_SHORT
from kmd.errors import ApiResultError
from kmd.llms.fuzzy_parsing import is_no_results
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.util.format_utils import fmt_lines
from kmd.util.log_calls import log_calls


log = get_logger(__name__)


def _litellm_completion(model: str, messages: List[Dict[str, str]]) -> str:
    llm_output = litellm.completion(
        model,
        messages=messages,
    )
    result = llm_output.choices[0].message.content  # type: ignore
    if not result or not isinstance(result, str):
        raise ApiResultError(f"LLM completion failed: {model}: {llm_output}")
    total_input_len = sum(len(m["content"]) for m in messages)
    log.message(
        f"LLM completion from {model}: input {total_input_len} chars in {len(messages)} messages, output {len(result)} chars"
    )
    return result


@log_calls(level="info")
def llm_completion(
    model: LLM,
    system_message: Message,
    template: MessageTemplate,
    input: str,
    save_objects: bool = True,
    check_no_results: bool = True,
) -> str:
    """
    Perform an LLM completion. Input is inserted into the template with a `body` parameter.
    Use this function to interact with the LLMs for consistent logging.
    """
    user_message = template.format(body=input)
    model_slug = slugify(model.value, separator="_")

    log.info(
        "LLM completion from %s on %s+%s chars system+user input…",
        model,
        len(system_message),
        len(user_message),
    )
    log.info(
        "LLM completion input to model %s:\n%s",
        model,
        fmt_lines(
            [
                abbreviate_str(f"System message: {str(system_message)}"),
                abbreviate_str(f"User message: {user_message}"),
            ]
        ),
    )

    text_output = _litellm_completion(
        model.value,
        messages=[
            {"role": "system", "content": str(system_message)},
            {"role": "user", "content": user_message},
        ],
    )

    log.info("LLM completion output:\n%s", indent(text_output, "    "))

    if check_no_results and is_no_results(text_output):
        log.message("No results for LLM transform, will ignore: %r", text_output)
        text_output = ""

    if save_objects:
        log.save_object(
            "LLM response",
            f"llm.{model_slug}",
            "\n\n".join(
                [
                    f"{HRULE_SHORT} System message {HRULE_SHORT}\n\n{str(system_message)}",
                    f"{HRULE_SHORT} User message {HRULE_SHORT}\n\n{user_message}",
                    f"{HRULE_SHORT} Response {HRULE_SHORT}\n\n{text_output}",
                ]
            ),
            level=LogLevel.message,
        )

    return text_output
