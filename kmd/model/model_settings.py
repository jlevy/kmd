from kmd.model.language_models import EmbeddingModel, LLM

# These are the default models for various actions.
# The user may override them with parameters.
DEFAULT_CAREFUL_LLM = LLM.o1_preview
DEFAULT_STRUCTURED_LLM = LLM.gpt_4o
DEFAULT_BASIC_LLM = LLM.claude_3_5_sonnet
DEFAULT_FAST_LLM = LLM.claude_3_haiku

DEFAULT_EMBEDDING_MODEL = EmbeddingModel.text_embedding_3_large
