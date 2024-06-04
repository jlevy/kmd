from contextlib import contextmanager
from textwrap import dedent
from typing import Generator, List
import re
from contextlib import contextmanager
from typing import Generator, cast
import marko
from marko.renderer import Renderer
from marko import block, inline


class MarkdownNormalizer(Renderer):
    """
    Render Markdown in normalized form.
    Based on: https://github.com/frostming/marko/blob/master/marko/md_renderer.py
    """

    def __init__(self) -> None:
        super().__init__()
        self._prefix: str = ""
        self._second_prefix: str = ""

    def __enter__(self) -> "MarkdownNormalizer":
        self._prefix = ""
        self._second_prefix = ""
        return super().__enter__()

    @contextmanager
    def container(self, prefix: str, second_prefix: str = "") -> Generator[None, None, None]:
        old_prefix, old_second_prefix = self._prefix, self._second_prefix
        self._prefix += prefix
        self._second_prefix += second_prefix
        yield
        self._prefix, self._second_prefix = old_prefix, old_second_prefix

    def render_paragraph(self, element: block.Paragraph) -> str:
        # FIXME: Wrap and break lines sensibly.
        children = self.render_children(element)
        line = f"{self._prefix}{children}\n"
        self._prefix = self._second_prefix
        return line

    def render_list(self, element: block.List) -> str:
        result: List[str] = []
        is_first = True
        if element.ordered:
            for num, child in enumerate(element.children, element.start):
                if not is_first:
                    result.append("\n")  # Normalize enumerated lists to have an additional newline.
                is_first = False
                with self.container(f"{num}. ", " " * (len(str(num)) + 2)):
                    result.append(self.render(child))
        else:
            for child in element.children:
                if not is_first:
                    result.append("\n")  # Normalize itemized lists to have an additional newline.
                is_first = False
                with self.container(f"{element.bullet} ", "  "):
                    result.append(self.render(child))
        self._prefix = self._second_prefix
        return "".join(result)

    def render_list_item(self, element: block.ListItem) -> str:
        return self.render_children(element)

    def render_quote(self, element: block.Quote) -> str:
        with self.container("> ", "> "):
            result = self.render_children(element).rstrip("\n")
        self._prefix = self._second_prefix
        return f"{result}\n"

    def render_fenced_code(self, element: block.FencedCode) -> str:
        extra = f" {element.extra}" if element.extra else ""
        lines = [f"{self._prefix}```{element.lang}{extra}"]
        lines.extend(
            f"{self._second_prefix}{line}" for line in self.render_children(element).splitlines()
        )
        lines.append(f"{self._second_prefix}```")
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"

    def render_code_block(self, element: block.CodeBlock) -> str:
        indent = " " * 4
        lines = self.render_children(element).splitlines()
        lines = [f"{self._prefix}{indent}{lines[0]}"] + [
            f"{self._second_prefix}{indent}{line}" for line in lines[1:]
        ]
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"

    def render_html_block(self, element: block.HTMLBlock) -> str:
        result = f"{self._prefix}{element.body}\n"
        self._prefix = self._second_prefix
        return result

    def render_thematic_break(self, element: block.ThematicBreak) -> str:
        result = f"{self._prefix}* * *\n"
        self._prefix = self._second_prefix
        return result

    def render_heading(self, element: block.Heading) -> str:
        result = f"{self._prefix}{'#' * element.level} {self.render_children(element)}\n"
        self._prefix = self._second_prefix
        return result

    def render_setext_heading(self, element: block.SetextHeading) -> str:
        return self.render_heading(cast("block.Heading", element))

    def render_blank_line(self, element: block.BlankLine) -> str:
        result = f"{self._prefix}\n"
        self._prefix = self._second_prefix
        return result

    def render_link_ref_def(self, element: block.LinkRefDef) -> str:
        link_text = element.dest
        if element.title:
            link_text += f" {element.title}"
        return f"[{element.label}]: {link_text}\n"

    def render_emphasis(self, element: inline.Emphasis) -> str:
        return f"*{self.render_children(element)}*"

    def render_strong_emphasis(self, element: inline.StrongEmphasis) -> str:
        return f"**{self.render_children(element)}**"

    def render_inline_html(self, element: inline.InlineHTML) -> str:
        return cast(str, element.children)

    def render_link(self, element: inline.Link) -> str:
        link_text = self.render_children(element)
        link_title = '"{}"'.format(element.title.replace('"', '\\"')) if element.title else None
        assert self.root_node
        label = next(
            (k for k, v in self.root_node.link_ref_defs.items() if v == (element.dest, link_title)),
            None,
        )
        if label is not None:
            if label == link_text:
                return f"[{label}]"
            return f"[{link_text}][{label}]"
        title = f" {link_title}" if link_title is not None else ""
        return f"[{link_text}]({element.dest}{title})"

    def render_auto_link(self, element: inline.AutoLink) -> str:
        return f"<{element.dest}>"

    def render_image(self, element: inline.Image) -> str:
        template = "![{}]({}{})"
        title = ' "{}"'.format(element.title.replace('"', '\\"')) if element.title else ""
        return template.format(self.render_children(element), element.dest, title)

    def render_literal(self, element: inline.Literal) -> str:
        return f"\\{element.children}"

    def render_raw_text(self, element: inline.RawText) -> str:
        from marko.ext.pangu import PANGU_RE

        return re.sub(PANGU_RE, " ", element.children)

    def render_line_break(self, element: inline.LineBreak) -> str:
        return "\n" if element.soft else "\\\n"

    def render_code_span(self, element: inline.CodeSpan) -> str:
        text = element.children
        if text and (text[0] == "`" or text[-1] == "`"):
            return f"`` {text} ``"
        return f"`{element.children}`"


def normalize_markdown(markdown_text: str) -> str:
    """
    Normalize Markdown text.
    """
    parsed = marko.parse(markdown_text)
    # TODO: Implement Flowmark Markdown wrapping here.
    result = MarkdownNormalizer().render(parsed)
    return result


## Tests


def test_normalize_markdown():
    original = dedent(
        """
        # This is a header

        This is a paragraph.

        - This is a list item
        - This is another list item

        A second paragraph.

        1. This is a numbered list item
        2. This is another numbered list item

        
        """
    ).lstrip()

    normalized = normalize_markdown(original)

    print("---Before")
    print(original)
    print("---After")
    print(normalized)

    assert (
        normalized
        == dedent(
            """
        # This is a header

        This is a paragraph.

        - This is a list item

        - This is another list item

        A second paragraph.

        1. This is a numbered list item

        2. This is another numbered list item
        """
        ).lstrip()
    )
