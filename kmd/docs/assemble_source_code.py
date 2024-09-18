import os
from pathlib import Path
from typing import List

from kmd.util.format_utils import fmt_path


kmd_base_path = Path(os.path.dirname(__file__)).parent


_TESTS_COMMENT_STR = "\n## Tests"


def _format_source_file(path: Path) -> str:
    with open(path, "r") as file:
        file_content = file.read()

    # Don't include any pytests that happen to be in the files.
    file_content = file_content.split(_TESTS_COMMENT_STR)[0] + "\n"

    header = f"\n\n# File {path.relative_to(kmd_base_path.parent)}:\n\n"
    footer = "\n\n"

    return header + file_content + footer


def _format_source_module(module_path: Path) -> str:
    source_files = [f for f in os.listdir(module_path) if f.endswith(".py") and f != "__init__.py"]
    output: List[str] = []

    for filename in source_files:
        output.append(_format_source_file(module_path / filename))

    return "".join(output)


def _format_file_or_module(path: Path) -> str:
    if path.is_file():
        return _format_source_file(path)
    elif path.is_dir():
        return _format_source_module(path)
    else:
        raise ValueError(f"Path for source not found (or not a file/directory): {fmt_path(path)}")


def source_for(*paths: Path) -> str:
    return "\n\n".join(_format_file_or_module(path) for path in paths)


model_src = source_for(kmd_base_path / "model")

base_action_defs_src = source_for(kmd_base_path / "action_defs" / "base_actions")

text_tool_src = source_for(
    kmd_base_path / "text_formatting",
    kmd_base_path / "lang_tools",
    kmd_base_path / "text_docs" / "text_doc.py",
)
