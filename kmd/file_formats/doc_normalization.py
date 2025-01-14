from pathlib import Path
from typing import Optional

from frontmatter_format import fmf_read, fmf_write

from kmd.errors import InvalidInput
from kmd.model.args_model import fmt_loc
from kmd.model.file_formats_model import detect_file_format, Format
from kmd.text_wrap.markdown_normalization import DEFAULT_WRAP_WIDTH, normalize_markdown
from kmd.text_wrap.text_wrapping import wrap_plaintext
from kmd.util.type_utils import not_none


def normalize_formatting(text: str, format: Format, width=DEFAULT_WRAP_WIDTH) -> str:
    """
    Normalize text formatting by wrapping lines and normalizing Markdown.
    """

    if format == Format.plaintext:
        return wrap_plaintext(text, width=width)
    elif format == Format.markdown or format == Format.md_html:
        return normalize_markdown(text)
    elif format == Format.html:
        # We don't currently auto-format HTML as we sometimes use HTML with specifically chosen line breaks.
        return text
    else:
        return text


def normalize_text_file(
    path: str | Path,
    target_path: Path,
    format: Optional[Format] = None,
) -> None:
    """
    Normalize formatting on a text file, handling Markdown, HTML, or text, as well as
    frontmatter, if present. `target_path` may be the same as `path`.
    """

    format = format or detect_file_format(path)
    if not format or not format.is_text:
        raise InvalidInput(f"Cannot format non-text files: {fmt_loc(path)}")

    content, metadata = fmf_read(path)
    norm_content = normalize_formatting(content, format=format)
    fmf_write(not_none(target_path), norm_content, metadata)
