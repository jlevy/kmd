"""
Auto-formatting of Markdown text.

This is similar to what is offered by
[markdownfmt](https://github.com/shurcooL/markdownfmt) but with a few
adaptations, including more aggressive normalization and wrapping of
lines semi-semantically (e.g. on sentence boundaries when appropriate).
(See [here](https://github.com/shurcooL/markdownfmt/issues/17) for
some old discussion on why line wrapping this way is convenient.)
"""

import re
from contextlib import contextmanager
from textwrap import dedent
from typing import Callable, cast, Generator, List, Protocol, Tuple

import marko
from marko import block, inline
from marko.block import HTMLBlock
from marko.parser import Parser
from marko.renderer import Renderer
from marko.source import Source

from kmd.lang_tools.sentence_split_regex import split_sentences_regex
from kmd.text_wrap.text_styling import CONSOLE_WRAP_WIDTH
from kmd.text_wrap.text_wrapping import wrap_length_fn, wrap_paragraph, wrap_paragraph_lines


class LineWrapper(Protocol):
    """Takes a text string and any indents to use, and returns the wrapped text."""

    def __call__(self, text: str, initial_indent: str, subsequent_indent: str) -> str: ...


class SentenceSplitter(Protocol):
    """Takes a text string and returns a list of sentences."""

    def __call__(self, text: str) -> List[str]: ...


def _normalize_html_comments(text: str, break_str: str = "\n\n") -> str:
    """
    Put HTML comments as standalone paragraphs.
    """

    # Small hack to avoid changing frontmatter format, for the rare corner
    # case where Markdown contains HTML-style frontmatter.
    def not_frontmatter(text: str) -> bool:
        return "<!---" not in text

    # TODO: Probably want do this for <div>s too.
    return _ensure_surrounding_breaks(
        text, [("<!--", "-->")], break_str=break_str, filter=not_frontmatter
    )


def _ensure_surrounding_breaks(
    html: str,
    tag_pairs: List[Tuple[str, str]],
    filter: Callable[[str], bool] = lambda _: True,
    break_str: str = "\n\n",
) -> str:
    for start_tag, end_tag in tag_pairs:
        pattern = re.compile(rf"(\s*{re.escape(start_tag)}.*?{re.escape(end_tag)}\s*)", re.DOTALL)

        def replacer(match: re.Match[str]) -> str:
            if not filter(match.group(0)):
                return match.group(0)

            content = match.group(1).strip()
            before = after = break_str

            if match.start() == 0:
                before = ""
            if match.end() == len(html):
                after = ""

            return f"{before}{content}{after}"

        html = re.sub(pattern, replacer, html)

    return html


# XXX Turn off Marko's parsing of block HTML.
# Block parsing with comments or block elements has some counterintuitive issues:
# https://github.com/frostming/marko/issues/202
# Another solution might be to always put a newline after a closing block tag during
# normalization, to avoid this confusion?
# For now, just ignoring block tags.
class CustomHTMLBlock(HTMLBlock):
    @classmethod
    def match(cls, source: Source) -> int | bool:
        return False


class CustomParser(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.block_elements["HTMLBlock"] = CustomHTMLBlock


class _MarkdownNormalizer(Renderer):
    """
    Render Markdown in normalized form. This is the internal implementation.
    You likely want to use `normalize_markdown()` instead.
    Based on: https://github.com/frostming/marko/blob/master/marko/md_renderer.py
    """

    def __init__(self, line_wrapper: LineWrapper) -> None:
        super().__init__()
        self._prefix: str = ""  # The prefix on the first line, with a bullet, such as `  - `.
        self._second_prefix: str = ""  # The prefix on subsequent lines, such as `    `.
        self._suppress_item_break: bool = True
        self._line_wrapper = line_wrapper

    def __enter__(self) -> "_MarkdownNormalizer":
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
            self._second_prefix,
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
            # Add the newline between paragraphs. Normally this would be an empty line but
            # within a quote block it would be the secondary prefix, like `> `.
            result += self._second_prefix.strip() + "\n"
        result += self.render_children(element)
        return result

    def render_quote(self, element: block.Quote) -> str:
        with self.container("> ", "> "):
            result = self.render_children(element).rstrip("\n")
        self._prefix = self._second_prefix
        return f"{result}\n"

    def _render_code(self, element: block.CodeBlock | block.FencedCode) -> str:
        # Preserve code content without reformatting.
        code_child = cast(inline.RawText, element.children[0])
        code_content = code_child.children.rstrip("\n")
        lang = element.lang if isinstance(element, block.FencedCode) else ""
        extra = element.extra if isinstance(element, block.FencedCode) else ""
        extra_text = f" {extra}" if extra else ""
        lang_text = f"{lang}{extra_text}" if lang else ""
        lines = [f"{self._prefix}```{lang_text}"]
        lines.extend(f"{self._second_prefix}{line}" for line in code_content.splitlines())
        lines.append(f"{self._second_prefix}```")
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"

    def render_fenced_code(self, element: block.FencedCode) -> str:
        return self._render_code(element)

    def render_code_block(self, element: block.CodeBlock) -> str:
        # Convert indented code blocks to fenced code blocks.
        return self._render_code(element)

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
        if self._prefix.strip():
            result = f"{self._prefix}\n"
        else:
            result = "\n"
        self._suppress_item_break = True
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


DEFAULT_WRAP_WIDTH = CONSOLE_WRAP_WIDTH
"""
Default wrap width for Markdown content. Currently same as console width.
"""


DEFAULT_MIN_LINE_LEN = 20
"""Default minimum line length for sentence breaking."""


def split_sentences_no_min_length(text: str) -> List[str]:
    return split_sentences_regex(text, min_length=0)


def wrap_lines_to_width(
    text: str, initial_indent: str, subsequent_indent: str, width: int = DEFAULT_WRAP_WIDTH
) -> str:
    """
    Wrap lines of text to a given width.
    """
    return wrap_paragraph(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
    )


def wrap_lines_using_sentences(
    text: str,
    initial_indent: str,
    subsequent_indent: str,
    split_sentences: SentenceSplitter = split_sentences_no_min_length,
    width: int = DEFAULT_WRAP_WIDTH,
    min_line_len: int = DEFAULT_MIN_LINE_LEN,
) -> str:
    """
    Wrap lines of text to a given width but also keep sentences on their own lines.
    If the last line ends up shorter than min_line_len, it's combined with the next sentence.
    """
    text = text.replace("\n", " ")
    lines: List[str] = []
    first_line = True
    length = wrap_length_fn
    initial_indent_len = wrap_length_fn(initial_indent)
    subsequent_indent_len = wrap_length_fn(subsequent_indent)

    sentences = split_sentences(text)

    for i, sentence in enumerate(sentences):
        current_column = initial_indent_len if first_line else subsequent_indent_len
        if len(lines) > 0 and length(lines[-1]) < min_line_len:
            current_column += length(lines[-1])

        wrapped = wrap_paragraph_lines(
            sentence,
            width=width,
            initial_column=current_column,
            subsequent_offset=subsequent_indent_len,
        )
        # If last line is shorter than min_line_len, combine with next line.
        # Also handles if the first word doesn't fit.
        if (
            len(lines) > 0
            and length(lines[-1]) < min_line_len
            and length(lines[-1]) + 1 + length(wrapped[0]) <= width
        ):
            lines[-1] += " " + wrapped[0]
            wrapped.pop(0)

        lines.extend(wrapped)

        first_line = False

    # Now insert the indents and assemble the paragraph.
    if initial_indent and len(lines) > 0:
        lines[0] = initial_indent + lines[0]
    if subsequent_indent and len(lines) > 1:
        lines[1:] = [subsequent_indent + line for line in lines[1:]]

    return "\n".join(lines)


def normalize_markdown(
    markdown_text: str, line_wrapper: LineWrapper = wrap_lines_using_sentences
) -> str:
    """
    Normalize Markdown text. Wraps lines and adds line breaks within paragraphs and on
    best-guess estimations of sentences, to make diffs more readable.

    Also enforces that all list items have two newlines between them, so that items
    are separate paragraphs when viewed as plaintext.
    """
    markdown_text = markdown_text.strip() + "\n"

    # If we want to normalize HTML blocks or comments.
    markdown_text = _normalize_html_comments(markdown_text)

    # Normalize the markdown and wrap lines.
    parser = CustomParser()
    parsed = parser.parse(markdown_text)
    result = _MarkdownNormalizer(line_wrapper).render(parsed)
    return result


def fill_markdown(markdown_text: str, dedent_input: bool = True) -> str:
    """
    Normalize and wrap Markdown text for reading on the console.
    Also dedents and strips the input, so it can be used on docstrings.
    """
    if dedent_input:
        markdown_text = dedent(markdown_text).strip()
    return normalize_markdown(markdown_text, line_wrapper=wrap_lines_to_width)


## Tests


def test_normalize_html_comments():
    input_text_1 = "<!--window-br--> Words and words"
    expected_output_1 = "<!--window-br-->\n\nWords and words"
    print(_normalize_html_comments(input_text_1))
    assert _normalize_html_comments(input_text_1) == expected_output_1


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

- This is a nice [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently.

A third paragraph.

## Sub-heading

1. This is a numbered list item
2. This is another numbered list item

<!--window-br-->

<!--window-br--> Words and words and words and words and words and <span data-foo="bar">some HTML</span> and words and words and words and words and words and words.

<span data-foo="bar">Inline HTML.</span> And some following words and words and words and words and words and words.

<h1 data-foo="bar">Block HTML.</h1> And some following words.

<div class="foo">
Some more HTML. Words and words and words and words and    words and <span data-foo="bar">more HTML</span> and words and words and words and words and words and words.</div>

> This is a quote block. With a couple sentences. Note we have a `>` on this line.
>
> - Quotes can also contain lists.
> - With items. Like this. And these items may have long sentences in them.

```python
def hello_world():
    print("Hello, World!")

# End of code
```


```
more code
```


Indented code:

    more code here

    and more

- **Intelligent:** Kmd understands itself. It reads its own code and docs and gives you assistance!


<p style="max-width: 450px;">
“*Simple should be simple.
Complex should be possible.*” —Alan Kay
</p>

### Building

1. Lorem ipsum dolor sit amet, consectetur adipiscing elit. [Fork](https://github.com/jlevy/kmd/fork) this repo
   (having your own fork
   will make it
   easier to contribute actions, add models, etc.).

2. [Check out](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
   the code. Lorem [another link](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

3. Install the package dependencies:

   ```shell
   poetry install
   ```
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
Seven. Eight. Nine. Ten.
A [link](https://example.com).
Some *emphasis* and **strong emphasis** and `code`. And a
super-super-super-super-super-super-super-hyphenated
veeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeery
long word.
This is a sentence with many words and words and words and words and words and
words and words and words.
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

- This is a nice
  [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently.

A third paragraph.

## Sub-heading

1. This is a numbered list item

2. This is another numbered list item

<!--window-br-->

<!--window-br-->

Words and words and words and words and words and <span data-foo="bar">some HTML</span>
and words and words and words and words and words and words.

<span data-foo="bar">Inline HTML.</span> And some following words and words and words
and words and words and words.

<h1 data-foo="bar">Block HTML.</h1> And some following words.

<div class="foo"> Some more HTML. Words and words and words and words and words and
<span data-foo="bar">more HTML</span> and words and words and words and words and words
and words.</div>

> This is a quote block.
> With a couple sentences.
> Note we have a `>` on this line.
> 
> - Quotes can also contain lists.
>
> - With items. Like this.
>   And these items may have long sentences in them.

```python
def hello_world():
    print("Hello, World!")

# End of code
```

```
more code
```

Indented code:

```
more code here

and more
```

- **Intelligent:** Kmd understands itself.
  It reads its own code and docs and gives you assistance!

<p style="max-width: 450px;"> “*Simple should be simple.
Complex should be possible.*” —Alan Kay </p>

### Building

1. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
   [Fork](https://github.com/jlevy/kmd/fork) this repo (having your own fork will make
   it easier to contribute actions, add models, etc.).

2. [Check out](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
   the code. Lorem
   [another link](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

3. Install the package dependencies:

   ```shell
   poetry install
   ```
    """
).lstrip()


def test_normalize_markdown():
    parsed = marko.parse(_original_doc)
    print("---Parsed")
    print(parsed)

    normalized_doc = normalize_markdown(_original_doc)

    print("---Before")
    print(_original_doc)
    print("---After")
    print(normalized_doc)

    assert normalized_doc == _expected_doc