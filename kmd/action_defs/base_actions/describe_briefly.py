from kmd.exec.action_builders import define_llm_action
from kmd.model.actions_model import LLMMessage, LLMTemplate, TitleTemplate
from kmd.config.settings import DEFAULT_CAREFUL_MODEL

define_llm_action(
    name="describe_briefly",
    description="Very brief description of text, in at most three sentences.",
    model=DEFAULT_CAREFUL_MODEL,
    system_message=LLMMessage(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    title_template=TitleTemplate("Summary of {title}"),
    template=LLMTemplate(
        """
        Give a brief description of the entire text below, as a summary of two or three sentences.
        Write it concisely and clearly, in a form suitable for a short description of a web page
        or article.

        - Use simple and precise language.

        - Simply state the facts or claims without referencing the text or the author. For example, if the
          text is about cheese being nutritious, you can say "Cheese is nutritious." But do NOT
          say "The author says cheese is nutritious" or "According to the text, cheese is nutritious."

        - If the content is missing so brief that it can't be described, simply say "(No description.)"
        
        Original text:

        {body}

        Brief description of the text:
        """
    ),
)
