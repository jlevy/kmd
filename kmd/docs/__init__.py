"""
Make docs and source code for kmd available to itself.
"""

from pathlib import Path

from kmd.docs.assemble_source_code import load_sources, SourceCode
from kmd.util.lazyobject import lazyobject
from kmd.util.string_template import StringTemplate


def _load_markdown(path: str) -> str:
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
        return _load_markdown(path)

    return content


welcome = _lazy_load("markdown/welcome")
what_is_kmd = _lazy_load("markdown/topics/a1_what_is_kmd")
motivation = _lazy_load("markdown/topics/a2_philosophy_of_kmd")
getting_started = _lazy_load("markdown/topics/a3_getting_started")
tips_for_use_with_other_tools = _lazy_load("markdown/topics/a4_tips_for_use_with_other_tools")
development = _lazy_load("markdown/topics/a5_development")

kmd_overview = _lazy_load("markdown/topics/b1_kmd_overview")
workspace_and_file_formats = _lazy_load("markdown/topics/b2_workspace_and_file_formats")
faq = _lazy_load("markdown/topics/b3_faq")


@lazyobject
def source_code() -> SourceCode:
    return load_sources()


@lazyobject
def api_docs() -> str:
    template_str = _load_markdown("markdown/api_docs_template")
    global source_code
    template_vars = list(source_code.__dict__.keys())
    template = StringTemplate(template_str, template_vars)
    return template.format(**source_code.__dict__)


@lazyobject
def assistant_instructions() -> str:
    return _load_markdown("markdown/assistant_instructions")
