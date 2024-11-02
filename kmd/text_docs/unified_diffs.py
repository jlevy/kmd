import difflib
from io import BytesIO
from typing import Optional

from patch_ng import PatchSet
from pydantic.dataclasses import dataclass

from kmd.config.logger import get_logger
from kmd.errors import ContentError
from kmd.model.file_formats_model import Format
from kmd.model.items_model import Item, ItemRelations, ItemType
from kmd.model.paths_model import StorePath
from kmd.util.log_calls import abbreviate_arg

log = get_logger(__name__)


@dataclass(frozen=True)
class UnifiedDiff:
    from_name: str
    to_name: str
    patch_text: str
    diffstat: str

    def __str__(self) -> str:
        return self.patch_text


def patch_set_to_str(patch_set: PatchSet) -> str:
    output = ""
    for p in patch_set.items:
        for headline in p.header:
            output += headline.decode().rstrip("\n") + "\n"
        output += "--- " + p.source.decode() + "\n"
        output += "+++ " + p.target.decode() + "\n"
        for h in p.hunks:
            output += "@@ -%d,%d +%d,%d @@%s\n" % (
                h.startsrc,
                h.linessrc,
                h.starttgt,
                h.linestgt,
                h.desc.decode(),
            )
            for line in h.text:
                output += line.decode()
    return output


def unified_diff(
    from_content: Optional[str],
    to_content: Optional[str],
    from_name: str = "before",
    to_name: str = "after",
) -> UnifiedDiff:
    lines1 = from_content.splitlines() if from_content else []
    lines2 = to_content.splitlines() if to_content else []

    # Generate the diff text using difflib
    diff_lines = difflib.unified_diff(
        lines1,
        lines2,
        fromfile=from_name,
        tofile=to_name,
        lineterm="",
    )
    diff_text = "\n".join(diff_lines)

    patch_set = PatchSet(BytesIO(diff_text.encode("utf-8")))
    if patch_set.errors > 0:
        raise ContentError(
            f"Had {patch_set.errors} errors parsing diff of `{from_name}` and `{to_name}`: {abbreviate_arg(diff_text)}"
        )

    return UnifiedDiff(from_name, to_name, patch_set_to_str(patch_set), str(patch_set.diffstat()))


def unified_diff_items(from_item: Item, to_item: Item) -> Item:
    if not from_item.body and not to_item.body:
        raise ContentError(f"No body to diff for {from_item} and {to_item}")
    if not from_item.store_path or not to_item.store_path:
        raise ContentError("No store path on items; save before diffing")
    if from_item.format != to_item.format:
        log.warning(
            "Diffing items of different formats: %s != %s", from_item.format, to_item.format
        )

    from_path, to_path = StorePath(from_item.store_path), StorePath(to_item.store_path)

    diff = unified_diff(from_item.body, to_item.body, str(from_path), str(to_path))

    return Item(
        type=ItemType.doc,
        format=Format.diff,
        relations=ItemRelations(diff_of=[from_path, to_path]),
        body=diff.patch_text,
    )
