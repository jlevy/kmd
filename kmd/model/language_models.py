from enum import Enum


class LLM(Enum):
    """
    We are using LiteLLM for models. For more see: https://docs.litellm.ai/docs/providers
    """

    gpt_4o = "gpt-4o"
    gpt_4 = "gpt-4"
    gpt_3_5_turbo = "gpt-3.5-turbo"

    claude_3_opus = "claude-3-opus-20240229"
    claude_3_sonnet = "claude-3-sonnet-20240229"
    claude_3_haiku = "claude-3-haiku-20240307"

    groq_llama3_8b_8192 = "groq/llama3-8b-8192"
    groq_llama3_70b_8192 = "groq/llama3-70b-8192"


MODEL_LIST = [model.value for model in LLM]


def get_model(model_name: str) -> LLM:
    # Look up model by key or value.
    try:
        return LLM[model_name]
    except KeyError:
        try:
            # Then by value:
            return LLM(model_name)
        except ValueError:
            raise ValueError(f"No model found with name: '{model_name}'")
