from typing import Dict, List
import litellm
from kmd.config.logger import get_logger


log = get_logger(__name__)


def completion(model: str, messages: List[Dict[str, str]]) -> str:
    log.message(f"Running LLM completion with {model}")
    llm_output = litellm.completion(
        model,
        messages=messages,
    )
    result = llm_output.choices[0].message.content  # type: ignore
    if not result or not isinstance(result, str):
        raise ValueError(f"LLM completion failed: {model}: {llm_output}")
    log.message(f"Got LLM completion: result length {len(result)}")
    return result
