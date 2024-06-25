from textwrap import indent
from slugify import slugify
from kmd.llms.completion import completion
from kmd.config.logger import get_logger
from kmd.util.log_calls import log_calls

log = get_logger(__name__)


@log_calls(level="info")
def llm_completion(
    model: str, system_message: str, template: str, input: str, save_objects: bool = True
) -> str:
    """
    Perform an LLM completion. Input is inserted into the template with a `body` parameter.
    Use this function to interact with the LLMs for consistent logging.
    """
    user_message = template.format(body=input)
    model_slug = slugify(model, separator="_")

    log.info("LLM completion input to model %s:\n%s", model, indent(user_message, "    "))
    if save_objects:
        log.save_object("System message", f"llm.{model_slug}", system_message)
        log.save_object("User message", f"llm.{model_slug}", user_message)

    text_output = completion(
        model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    log.info("LLM completion output:\n%s", indent(text_output, "    "))
    if save_objects:
        log.save_object("LLM output", f"llm.{model_slug}", text_output)

    return text_output
