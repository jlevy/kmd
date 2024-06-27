from typing import Dict, List
import litellm
from kmd.config.logger import get_logger
from kmd.model.errors_model import ApiResultError


log = get_logger(__name__)


def completion(model: str, messages: List[Dict[str, str]]) -> str:
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
