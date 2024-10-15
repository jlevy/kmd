"""
Make docs and source code for kmd available to itself.
"""

from pathlib import Path

from kmd.docs.assemble_source_code import load_sources, SourceCode
from kmd.util.lazyobject import lazyobject


def _load_markdown(path: str) -> str:
    if not path.endswith(".md"):
        path += ".md"
    base_dir = Path(__file__).parent
    topic_file = base_dir / path
    if not topic_file.exists():
        raise ValueError(f"Unknown doc: {topic_file}")

    return topic_file.read_text()


@lazyobject
def welcome() -> str:
    return _load_markdown("markdown/welcome")


@lazyobject
def about_kmd() -> str:
    return _load_markdown("markdown/topics/about_kmd")


@lazyobject
def workspace_and_file_formats() -> str:
    return _load_markdown("markdown/topics/workspace_and_file_formats")


@lazyobject
def faq() -> str:
    return _load_markdown("markdown/topics/faq")


@lazyobject
def source_code() -> SourceCode:
    return load_sources()


@lazyobject
def api_docs() -> str:
    template_str = _load_markdown("markdown/api_docs_template")
    global source_code
    return template_str.format(
        model_src=source_code.model_src,
        base_action_defs_src=source_code.base_action_defs_src,
        text_tool_src=source_code.text_tool_src,
    )


@lazyobject
def assistant_instructions() -> str:
    return _load_markdown("markdown/assistant_instructions")
