"""
Make docs and source code for kmd available to itself.
"""

from pathlib import Path

from kmd.config.logger import get_logger
from kmd.docs.assemble_source_code import load_source_code, SourceCode
from kmd.util.lazyobject import lazyobject
from kmd.util.string_template import StringTemplate


log = get_logger(__name__)


def _load_help_src(path: str) -> str:
    if not path.endswith(".md"):
        path += ".md"
    base_dir = Path(__file__).parent
    topic_file = base_dir / path
    if not topic_file.exists():
        raise ValueError(f"Unknown doc: {topic_file}")

    return topic_file.read_text()


def _lazy_load(path: str):
    @lazyobject
    def content() -> str:
        return _load_help_src(path)

    return content


welcome = _lazy_load("markdown/welcome")
what_is_kmd = _lazy_load("markdown/topics/a1_what_is_kmd")
motivation = _lazy_load("markdown/topics/a2_philosophy_of_kmd")
installation = _lazy_load("markdown/topics/a3_installation")
getting_started = _lazy_load("markdown/topics/a4_getting_started")
tips_for_use_with_other_tools = _lazy_load("markdown/topics/a5_tips_for_use_with_other_tools")
development = _lazy_load("markdown/topics/a6_development")

kmd_overview = _lazy_load("markdown/topics/b1_kmd_overview")
workspace_and_file_formats = _lazy_load("markdown/topics/b2_workspace_and_file_formats")
faq = _lazy_load("markdown/topics/b3_faq")


@lazyobject
def source_code() -> SourceCode:
    return load_source_code()


@lazyobject
def api_docs() -> str:
    template_str = _load_help_src("markdown/api_docs_template")
    global source_code
    template_vars = list(source_code.__dict__.keys())
    template = StringTemplate(template_str, template_vars)
    return template.format(**source_code.__dict__)


@lazyobject
def assistant_instructions() -> str:
    template = StringTemplate(
        _load_help_src("markdown/assistant_instructions_template"), ["assistant_response_model"]
    )
    model_src = load_source_code().assistant_response_model_src
    model_src_lines = len(model_src.strip().splitlines())
    instructions = template.format(assistant_response_model=model_src)
    instructions_lines = len(instructions.strip().splitlines())
    log.info(
        "Loaded assistant instructions: %s lines, assistant model: %s lines",
        instructions_lines,
        model_src_lines,
    )
    assert instructions_lines > 100 and model_src_lines > 10
    return instructions
