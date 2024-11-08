"""
The core classes for modeling kmd's framework.

We include essential logic here but try to keep logic and dependencies minimal.
"""

from kmd.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
    PathOp,
    PathOpType,
    PerItemAction,
    TitleTemplate,
)
from kmd.model.args_model import (
    ANY_ARGS,
    ArgCount,
    CommandArg,
    fmt_loc,
    is_store_path,
    Locator,
    NO_ARGS,
    ONE_ARG,
    ONE_OR_MORE_ARGS,
    ONE_OR_NO_ARGS,
    TWO_ARGS,
    TWO_OR_MORE_ARGS,
)
from kmd.model.canon_url import canonicalize_url, thumbnail_url
from kmd.model.compound_actions_model import ComboAction, look_up_actions, SequenceAction
from kmd.model.doc_elements import (
    ANNOTATED_PARA,
    CHUNK,
    CITATION,
    CONCEPTS,
    DATA_TIMESTAMP,
    DESCRIPTION,
    FRAME_CAPTURE,
    FULL_TEXT,
    GROUP,
    ORIGINAL,
    PARA,
    PARA_CAPTION,
    RESULT,
    SPEAKER_LABEL,
    SUMMARY,
)

from kmd.model.file_formats_model import (
    canonicalize_file_ext,
    FileExt,
    Format,
    is_ignored,
    parse_file_ext,
    split_filename,
)
from kmd.model.graph_model import GraphData, Link, Node
from kmd.model.items_model import (
    IdType,
    Item,
    ItemId,
    ItemRelations,
    ItemType,
    SLUG_MAX_LEN,
    State,
    UNTITLED,
)
from kmd.model.language_models import EmbeddingModel, LLM
from kmd.model.llm_actions_model import ChunkedLLMAction, LLMAction
from kmd.model.media_model import (
    HeatmapValue,
    MediaMetadata,
    MediaService,
    MediaType,
    MediaUrlType,
    SERVICE_APPLE_PODCASTS,
    SERVICE_VIMEO,
    SERVICE_YOUTUBE,
)
from kmd.model.messages_model import Message, MessageTemplate

# flake8: noqa: F401


from kmd.model.model_settings import DEFAULT_CAREFUL_LLM, DEFAULT_EMBEDDING_MODEL, DEFAULT_FAST_LLM
from kmd.model.params_model import (
    ALL_COMMON_PARAMS,
    COMMON_ACTION_PARAMS,
    common_param,
    common_params,
    GLOBAL_PARAMS,
    Param,
    ParamList,
    ParamValues,
    RUNTIME_ACTION_PARAMS,
    USER_SETTABLE_PARAMS,
)
from kmd.model.paths_model import StorePath
from kmd.model.preconditions_model import Precondition, precondition
from kmd.model.shell_model import ShellResult
