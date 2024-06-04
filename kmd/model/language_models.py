from enum import Enum


class LLM(Enum):
    """
    We are using LiteLLM for models. For more see: https://docs.litellm.ai/docs/providers
    """

    gpt_3_5_turbo_16k_0613 = "gpt-3.5-turbo-16k-0613"
    gpt_4 = "gpt-4"
    gpt_4_turbo = "gpt-4-turbo"
    gpt_4o = "gpt-4o"

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
