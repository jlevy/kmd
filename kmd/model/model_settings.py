from kmd.model.language_models import LLM, EmbeddingModel

# These are the default models for various actions.
# The user may override them with parameters.
DEFAULT_CAREFUL_LLM = LLM.gpt_4o  # noqa: F821
DEFAULT_FAST_LLM = LLM.gpt_4o_mini

DEFAULT_EMBEDDING_MODEL = EmbeddingModel.text_embedding_3_large
