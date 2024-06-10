from contextlib import contextmanager
from textwrap import dedent
import textwrap
from typing import Callable, Generator, List
import re
from contextlib import contextmanager
from typing import Generator, cast
import marko
from marko.renderer import Renderer
from marko import block, inline
from kmd.lang_tools.sentence_split_regex import split_sentences_fast


class MarkdownNormalizer(Renderer):
    """
    Render Markdown in normalized form.

    Also enforces that all line items have two newlines between them, so that items
    are separate paragraphs when viewed as plaintext.

    Based on: https://github.com/frostming/marko/blob/master/marko/md_renderer.py
    """

    def __init__(self, line_wrapper: Callable[[str, str, str], str]) -> None:
        super().__init__()
        self._prefix: str = ""
        self._second_prefix: str = ""
        self._suppress_item_break: bool = True
        self._line_wrapper = line_wrapper

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
        # Suppress item breaks on list items following a top-level paragraph.
        if not self._prefix:
            self._suppress_item_break = True
        children = self.render_children(element)
        wrapped_text = self._line_wrapper(
            children,
            self._prefix,
            " " * len(self._prefix),
        )
        self._prefix = self._second_prefix
        return wrapped_text + "\n"

    def render_list(self, element: block.List) -> str:
        result: List[str] = []
        if element.ordered:
            for num, child in enumerate(element.children, element.start):
                with self.container(f"{num}. ", " " * (len(str(num)) + 2)):
                    result.append(self.render(child))
        else:
            for child in element.children:
                with self.container(f"{element.bullet} ", "  "):
                    result.append(self.render(child))

        self._prefix = self._second_prefix
        return "".join(result)

    def render_list_item(self, element: block.ListItem) -> str:
        result = ""
        # We want all list items to have two newlines between them.
        if self._suppress_item_break:
            self._suppress_item_break = False
        else:
            result += "\n"
        result += self.render_children(element)
        return result

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
        result = f"{self._prefix}{element.body}"
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


DEFAULT_WRAP_WIDTH = 92
"""Default wrap width for text content. Same as Flowmark."""
# See https://github.com/jlevy/atom-flowmark/blob/master/lib/remark-smart-word-wrap.js#L13


def wrap_lines_and_break_sentences(
    text: str,
    initial_indent: str,
    subsequent_indent: str,
    split_sentences: Callable[[str], List[str]] = split_sentences_fast,
    width: int = DEFAULT_WRAP_WIDTH,
) -> str:
    """
    Wrap lines of text to a given width but also keep sentences on their own lines.
    """
    text = text.replace("\n", " ")
    wrapped_lines = []
    first_line = True
    for line in text.splitlines():
        if not line.strip():
            wrapped_lines.append("")
        else:
            sentences = split_sentences(line)
            wrapped_lines.extend(
                textwrap.fill(
                    sentence,
                    width=width,
                    initial_indent=initial_indent if first_line else subsequent_indent,
                    subsequent_indent=subsequent_indent,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                for sentence in sentences
            )
        first_line = False
    return "\n".join(wrapped_lines)


def normalize_markdown(markdown_text: str) -> str:
    """
    Normalize Markdown text. Wraps lines and adds line breaks within paragraphs and on
    best-guess estimations of sentences, to make diffs more readable.
    """
    markdown_text = markdown_text.strip() + "\n"

    # Normalize the markdown and wrap lines.
    parsed = marko.parse(markdown_text)
    result = MarkdownNormalizer(wrap_lines_and_break_sentences).render(parsed)
    return result


## Tests


_original_doc = dedent(
    """
    # This is a header

    This is sentence one. This is sentence two.
    This is sentence three.
    This is sentence four. This is sentence 5. This is sentence six.
    Seven. Eight. Nine. Ten.
    A [link](https://example.com). Some *emphasis* and **strong emphasis** and `code`.
    And a     super-super-super-super-super-super-super-hyphenated veeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeery long word.
    This is a sentence with many words and words and words and words and words and words and words and words.
    And another with words and
    words and words split across a line.

    A second paragraph.


    - This is a list item
    - This is another list item
        - A sub item
          - A sub sub item
    - This is a third list item with many words and words and words and words and words and words and words and words
      - A sub item
      - Another sub item

      - Another sub item (after a line break)

    A third paragraph.

    ## Sub-heading

    1. This is a numbered list item
    2. This is another numbered list item

    
    <!--window-br-->
    
    <span data-foo="bar">Some HTML.</span>

    > This is a quote block. With a couple sentences.
    """
).lstrip()

_expected_doc = dedent(
    """
    # This is a header

    This is sentence one.
    This is sentence two.
    This is sentence three.
    This is sentence four.
    This is sentence 5. This is sentence six.
    Seven. Eight. Nine.
    Ten. A [link](https://example.com).
    Some *emphasis* and **strong emphasis** and `code`. And a
    super-super-super-super-super-super-super-hyphenated
    veeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeery
    long word.
    This is a sentence with many words and words and words and words and words and words and
    words and words.
    And another with words and words and words split across a line.

    A second paragraph.

    - This is a list item

    - This is another list item

      - A sub item

        - A sub sub item

    - This is a third list item with many words and words and words and words and words and
      words and words and words

      - A sub item

      - Another sub item

      - Another sub item (after a line break)

    A third paragraph.

    ## Sub-heading

    1. This is a numbered list item

    2. This is another numbered list item

    <!--window-br-->

    <span data-foo="bar">Some HTML.</span>

    > This is a quote block.
    > With a couple sentences.
    """
).lstrip()


def test_normalize_markdown():

    normalized_doc = normalize_markdown(_original_doc)

    print("---Before")
    print(_original_doc)
    print("---After")
    print(normalized_doc)

    assert normalized_doc == _expected_doc
