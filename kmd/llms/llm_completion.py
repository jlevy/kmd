from typing import Dict, List
from textwrap import indent
from slugify import slugify
import litellm
from kmd.config.logger import get_logger
from kmd.model.actions_model import LLMTemplate
from kmd.model.errors_model import ApiResultError
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
    log.info(
        f"Got LLM completion from {model}: input {total_input_len} chars in {len(messages)} messages, result {len(result)} chars"
    )
    return result


@log_calls(level="info")
def llm_completion(
    model: str, system_message: str, template: LLMTemplate, input: str, save_objects: bool = True
) -> str:
    """
    Perform an LLM completion. Input is inserted into the template with a `body` parameter.
    Use this function to interact with the LLMs for consistent logging.
    """
    user_message = template.format(body=input)
    model_slug = slugify(model, separator="_")

    log.info("LLM completion input to model %s:\n%s", model, indent(user_message, "    "))
    if save_objects:
        log.save_object(
            "LLM request",
            f"llm.{model_slug}",
            f"""System message: {system_message}\n\nUser message: {user_message}\n""",
        )

    text_output = _litellm_completion(
        model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    log.info("LLM completion output:\n%s", indent(text_output, "    "))
    if save_objects:
        log.save_object("LLM response", f"llm.{model_slug}", text_output)

    return text_output
