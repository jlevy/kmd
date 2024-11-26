from pathlib import Path

from frontmatter_format import fmf_read, fmf_read_frontmatter_raw

from kmd.config.logger import get_logger
from kmd.file_formats.chat_format import ChatHistory
from kmd.model.file_formats_model import file_format_info
from kmd.model.items_model import ItemType
from kmd.shell.shell_output import cprint, Wrap
from kmd.text_chunks.parse_divs import parse_divs
from kmd.util.format_utils import fmt_file_size

log = get_logger(__name__)


def _dual_format_size(size: int):
    readable_size_str = ""
    if size > 1000000:
        readable_size = fmt_file_size(size)
        readable_size_str += f" ({readable_size})"
    return f"{size} bytes{readable_size_str}"


def print_file_info(
    input_path: Path, slow: bool = False, show_size_details: bool = False, show_format: bool = False
):
    # Format info.
    detected_format = None
    if show_format:
        format_info = file_format_info(input_path)
        cprint(f"format: {format_info.as_str()}", text_wrap=Wrap.NONE)
        detected_format = format_info.format

    # Size info.
    size = Path(input_path).stat().st_size
    cprint(f"size: {_dual_format_size(size)}", text_wrap=Wrap.NONE)

    # Raw frontmatter info.
    try:
        _frontmatter_str, offset = fmf_read_frontmatter_raw(input_path)
    except UnicodeDecodeError:
        offset = None

    # Structured frontmatter and content info.
    body = None
    if show_size_details and detected_format and detected_format.supports_frontmatter:
        try:
            body, frontmatter = fmf_read(input_path)

            item_type = None
            if frontmatter:
                if offset:
                    cprint(
                        f"frontmatter: {len(frontmatter)} keys, {_dual_format_size(offset)}",
                        text_wrap=Wrap.NONE,
                    )
                item_type = frontmatter.get("type")
                if item_type:
                    cprint(f"item type: {item_type}", text_wrap=Wrap.NONE)
            if body:
                # Show chat history info.
                if item_type and item_type == ItemType.chat.value:
                    try:
                        chat_history = ChatHistory.from_yaml(body)
                        size_summary_str = chat_history.size_summary()
                        cprint(f"chat history: {size_summary_str}", text_wrap=Wrap.NONE)
                    except Exception:
                        pass
                # Parse text body.
                parsed_body = parse_divs(body)
                size_summary_str = parsed_body.size_summary(fast=not slow)
                cprint(f"body: {size_summary_str}", text_wrap=Wrap.NONE)
        except UnicodeDecodeError as e:
            log.warning("Error reading content as text, skipping body: %s", e)

    else:
        if offset:
            cprint(f"frontmatter: {_dual_format_size(offset)}", text_wrap=Wrap.NONE)
