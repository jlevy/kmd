import os
from pathlib import Path
from typing import List

from cachetools import cached
from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.util.format_utils import fmt_path
from kmd.util.strif import lenb

log = get_logger(__name__)

kmd_base_path = Path(os.path.dirname(__file__)).parent


_TESTS_COMMENT_STR = "\n## Tests"

_SOURCE_SEPARATOR = "\n---\n"


def _format_source_file(path: Path) -> str:
    with open(path, "r") as file:
        file_content = file.read()

    # Don't include any pytests that happen to be in the files.
    file_content = file_content.split(_TESTS_COMMENT_STR)[0]
    file_content = file_content.rstrip("\n") + "\n"

    header = f"# File {path.relative_to(kmd_base_path.parent)}:\n\n"

    return header + (file_content if file_content.strip() else "(empty)")


def _format_source_module(module_path: Path) -> str:
    source_files = [f for f in os.listdir(module_path) if f.endswith(".py")]
    output: List[str] = []

    for filename in source_files:
        if source_code := _format_source_file(module_path / filename):
            output.append(source_code)

    return _SOURCE_SEPARATOR.join(output)


def _format_file_or_module(path: Path) -> str:
    if path.is_file():
        return _format_source_file(path)
    elif path.is_dir():
        return _format_source_module(path)
    else:
        raise ValueError(f"Path for source not found (or not a file/directory): {fmt_path(path)}")


def read_source_code(*paths: Path) -> str:
    """
    Get the source code for the given paths, formatted in a format friendly for an LLM.
    """
    return _SOURCE_SEPARATOR.join(filter(None, (_format_file_or_module(path) for path in paths)))


@dataclass(frozen=True)
class SourceCode:
    model_src: str
    """The source code for the kmd framework model."""

    assistant_model_src: str
    """The source code for the assistant model."""

    base_action_defs_src: str
    """The source code for all the base action definitions."""

    text_tool_src: str
    """The source code for some generally useful text tools."""

    file_formats_src: str
    """Documentation and source for common file formats."""

    example_action_src: str
    """Source code for an example action."""

    def __str__(self) -> str:
        sizes = ", ".join(
            f"{k} {len(v.splitlines())} lines ({lenb(v)})" for k, v in self.__dict__.items()
        )
        return f"SourceCode({sizes})"


@cached(cache={})
def load_source_code() -> SourceCode:
    code = SourceCode(
        model_src=read_source_code(kmd_base_path / "model"),
        assistant_model_src=read_source_code(
            kmd_base_path / "model" / "assistant_response_model.py",
        ),
        base_action_defs_src=read_source_code(kmd_base_path / "action_defs" / "base_actions"),
        text_tool_src=read_source_code(
            kmd_base_path / "text_formatting",
            kmd_base_path / "lang_tools",
            kmd_base_path / "text_docs" / "text_doc.py",
        ),
        file_formats_src=read_source_code(kmd_base_path / "file_formats"),
        example_action_src=read_source_code(
            kmd_base_path / "action_defs" / "base_actions" / "strip_html.py",
            kmd_base_path / "action_defs" / "base_actions" / "describe_briefly.py",
        ),
    )
    log.info("Loaded sources: %s", str(code))
    return code
