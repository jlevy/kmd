from dataclasses import dataclass, field
from typing import List, Optional
from kmd.text_formatting.html_in_md import div_wrapper


@dataclass
class TextNode:
    """
    A node in parsed structured text, with refernce offsets into the original text.
    Useful for parsing Markdown broken into div tags.
    """

    original_text: str

    # Offsets into the original text.
    offset: int
    content_start: int
    content_end: int

    tag_name: Optional[str] = None
    class_name: Optional[str] = None
    begin_marker: Optional[str] = None
    end_marker: Optional[str] = None

    children: List["TextNode"] = field(default_factory=list)

    @property
    def end_offset(self) -> int:
        assert self.content_end >= 0
        return self.content_end + len(self.end_marker) if self.end_marker else self.content_end

    @property
    def contents(self) -> str:
        return self.original_text[self.content_start : self.content_end]

    def is_whitespace(self) -> bool:
        return not self.children and self.contents.strip() == ""

    def children_by_class_names(self, *class_names: str) -> List["TextNode"]:
        return [child for child in self.children if child.class_name in class_names]

    def child_by_class_name(self, class_name: str) -> Optional["TextNode"]:
        nodes = self.children_by_class_names(class_name)
        if len(nodes) == 0:
            return None
        if len(nodes) > 1:
            raise ValueError(f"Multiple children with class name {class_name}")
        return nodes[0]

    def reassemble(self, padding: str = "\n\n") -> str:
        """
        Reassemble as string. If padding is provided (not ""), then strip, skip whitespace,
        and insert our own padding.
        """
        strip_fn = lambda s: s.strip() if padding else s
        skip_whitespace = bool(padding)

        if not self.children:
            if not self.tag_name:
                return strip_fn(self.contents)
            else:
                wrap = div_wrapper(self.class_name, padding=padding)
                return wrap(strip_fn(self.contents))
        else:
            padded_children = (padding or "").join(
                child.reassemble(padding)
                for child in self.children
                if (not skip_whitespace or not child.is_whitespace())
            )
            if not self.tag_name:
                return padded_children
            else:
                wrap = div_wrapper(self.class_name, padding=padding)
                return wrap(padded_children)

    def __str__(self):
        return self._str_recursive()

    def _str_recursive(self, level: int = 0, max_len: int = 40) -> str:
        indent = "    " * level
        content_preview = self.contents
        if len(content_preview) > max_len:
            content_preview = content_preview[:20] + " ... " + content_preview[-20:]
        result = (
            f"{indent}TextNode(tag_name={self.tag_name} class_name={self.class_name} offset={self.offset},"
            f" content_start={self.content_start}, content_end={self.content_end}) "
            f"{repr(content_preview)}\n"
        )
        for child in self.children:
            result += child._str_recursive(level + 1)
        return result
