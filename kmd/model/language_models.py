from enum import Enum


class LLM(Enum):
    """
    We are using LiteLLM for models.

    For current list of models see: https://docs.litellm.ai/docs/providers
    """

    o1_mini = "o1-mini"
    o1_preview = "o1-preview"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4o = "gpt-4o"
    gpt_4 = "gpt-4"
    gpt_3_5_turbo = "gpt-3.5-turbo"

    claude_3_5_sonnet = "claude-3-5-sonnet-20240620"
    claude_3_opus = "claude-3-opus-20240229"
    claude_3_sonnet = "claude-3-sonnet-20240229"
    claude_3_haiku = "claude-3-haiku-20240307"

    groq_llama_3_1_8b_instant = "groq/llama-3.1-8b-instant"
    groq_llama_3_1_70b_versatile = "groq/llama-3.1-70b-versatile"
    groq_llama_3_1_405b_reasoning = "groq/llama-3.1-405b-reasoning"
    groq_llama3_8b_8192 = "groq/llama3-8b-8192"
    groq_llama3_70b_8192 = "groq/llama3-70b-8192"

    def __str__(self):
        return self.value


LLM_LIST = [model.value for model in LLM]


class EmbeddingModel(Enum):
    """
    LiteLLM embedding models.

    For current list of models see: https://docs.litellm.ai/docs/embedding/supported_embedding
    """

    text_embedding_3_large = "text-embedding-3-large"
    text_embedding_3_small = "text-embedding-3-small"
