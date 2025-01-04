from pathlib import Path

from frontmatter_format import fmf_read, fmf_read_frontmatter_raw

from kmd.config.logger import get_logger
from kmd.file_formats.chat_format import ChatHistory
from kmd.model.file_formats_model import file_format_info
from kmd.model.items_model import ItemType
from kmd.shell_ui.shell_output import cprint, format_name_and_value
from kmd.text_chunks.parse_divs import parse_divs
from kmd.text_wrap.text_styling import Wrap
from kmd.util.format_utils import fmt_size_dual

log = get_logger(__name__)


def print_dir_info(path: Path, text_wrap: Wrap = Wrap.NONE):
    total_size = 0
    file_count = 0

    # Iterate through all files in directory and subdirectories.
    for file_path in path.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size

    cprint(format_name_and_value("total files", f"{file_count}"), text_wrap=text_wrap)
    cprint(format_name_and_value("total size", fmt_size_dual(total_size)), text_wrap=text_wrap)


def print_file_info(
    input_path: Path,
    slow: bool = False,
    show_size_details: bool = False,
    show_format: bool = False,
    text_wrap: Wrap = Wrap.NONE,
):
    if input_path.is_dir():
        print_dir_info(input_path, text_wrap)
        return

    # Format info.
    detected_format = None
    if show_format:
        format_info = file_format_info(input_path)
        cprint(format_name_and_value("format", format_info.as_str()), text_wrap=text_wrap)
        detected_format = format_info.format

    # Size info.
    size = Path(input_path).stat().st_size
    cprint(format_name_and_value("size", fmt_size_dual(size)), text_wrap=text_wrap)

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
                        format_name_and_value(
                            "frontmatter",
                            f"{len(frontmatter)} keys, {fmt_size_dual(offset)}",
                        ),
                        text_wrap=text_wrap,
                    )
                item_type = frontmatter.get("type")
                if item_type:
                    cprint(
                        format_name_and_value("item type", item_type),
                        text_wrap=text_wrap,
                    )
            if body:
                # Show chat history info.
                if item_type and item_type == ItemType.chat.value:
                    try:
                        chat_history = ChatHistory.from_yaml(body)
                        size_summary_str = chat_history.size_summary()
                        cprint(
                            format_name_and_value("chat history", size_summary_str),
                            text_wrap=text_wrap,
                        )
                    except Exception:
                        pass
                # Parse text body.
                parsed_body = parse_divs(body)
                size_summary_str = parsed_body.size_summary(fast=not slow)
                cprint(
                    format_name_and_value("body", size_summary_str, text_wrap=Wrap.NONE),
                    text_wrap=Wrap.NONE,
                )
        except UnicodeDecodeError as e:
            log.warning("Error reading content as text, skipping body: %s", e)

    else:
        if offset:
            cprint(
                format_name_and_value("frontmatter", fmt_size_dual(offset)),
                text_wrap=text_wrap,
            )
