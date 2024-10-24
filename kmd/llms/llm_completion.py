from typing import cast, Dict, List, Optional, Type, Union

import litellm
from litellm.types.utils import Choices, Message as LiteLLMMessage, ModelResponse
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from slugify import slugify

from kmd.config.logger import get_logger
from kmd.config.settings import LogLevel
from kmd.errors import ApiResultError
from kmd.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole
from kmd.llms.fuzzy_parsing import is_no_results
from kmd.model.language_models import LLM
from kmd.model.messages_model import Message, MessageTemplate
from kmd.util.format_utils import fmt_lines
from kmd.util.log_calls import log_calls
from kmd.util.strif import abbreviate_str


log = get_logger(__name__)


@dataclass
class LLMCompletionResult:
    message: LiteLLMMessage
    content: str


@log_calls(level="info")
def llm_completion(
    model: str | LLM,
    messages: List[Dict[str, str]],
    response_format: Optional[Union[dict, Type[BaseModel]]] = None,
    **kwargs,
) -> LLMCompletionResult:
    """
    Perform an LLM completion with LiteLLM.
    """
    model_name = model if isinstance(model, str) else model.value

    llm_output = cast(
        ModelResponse,
        litellm.completion(
            model_name,
            messages=messages,
            response_format=response_format,
            **kwargs,
        ),  # type: ignore
    )

    choices = cast(Choices, llm_output.choices[0])

    message = choices.message

    # Just sanity checking and logging.
    content = choices.message.content
    if not content or not isinstance(content, str):
        raise ApiResultError(f"LLM completion failed: {model}: {llm_output}")

    total_input_len = sum(len(m["content"]) for m in messages)
    log.message(
        f"LLM completion from {model}: input {total_input_len} chars in {len(messages)} messages, output {len(content)} chars"
    )

    return LLMCompletionResult(message=message, content=content)


def llm_template_completion(
    model: LLM,
    system_message: Message,
    template: MessageTemplate,
    input: str,
    save_objects: bool = True,
    check_no_results: bool = True,
    response_format: Optional[Union[dict, Type[BaseModel]]] = None,
    **kwargs,
) -> LLMCompletionResult:
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

    result = llm_completion(
        model,
        messages=[
            {"role": "system", "content": str(system_message)},
            {"role": "user", "content": user_message},
        ],
        response_format=response_format,
        **kwargs,
    )

    if check_no_results and is_no_results(result.content):
        log.message("No results for LLM transform, will ignore: %r", result.content)
        result.content = ""

    if save_objects:
        messages = ChatHistory(
            [
                ChatMessage(ChatRole.system, str(system_message)),
                ChatMessage(ChatRole.user, user_message),
                ChatMessage(ChatRole.assistant, result.content),
            ]
        )
        log.save_object(
            "LLM response",
            f"llm.{model_slug}",
            messages.to_yaml(),
            level=LogLevel.message,
        )

    return result
