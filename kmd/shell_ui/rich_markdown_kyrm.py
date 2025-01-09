import re

from textwrap import dedent
from typing import Callable

from markdown_it.token import Token
from rich.console import Console, ConsoleOptions, RenderResult
from rich.padding import Padding
from rich.text import Text

from kmd.config.settings import global_settings
from kmd.config.text_styles import COLOR_COMMENT, STYLE_CODE
from kmd.shell_ui.kyrm_codes import Kri, KriLink, TextAttrs, TextTooltip, UIAction, UIActionType

from kmd.shell_ui.rich_markdown_custom import CodeBlock, Markdown


Transform = Callable[[str], Text]


class TransformingCodeBlock(CodeBlock):
    """
    CodeBlock that applies a transform to its content.
    """

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> "TransformingCodeBlock":
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        # Retrieve the code_transform from the markdown instance.
        code_transform = getattr(markdown, "code_transform", None)
        return cls(lexer_name or "text", markdown.code_theme, transform=code_transform)

    def __init__(self, lexer_name: str, theme: str, transform: Transform | None = None) -> None:
        super().__init__(lexer_name, theme)
        self.transform = transform

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        code = str(self.text).rstrip()
        if self.transform:
            code = self.transform(code)

        yield Padding(code, pad=(1, 0, 1, 0))

        # Previously, we used syntax highlighting, but right now having transform do it.
        # yield Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=1)


class TransformingMarkdown(Markdown):
    """
    Customize Rich's Markdown to apply a transform to code blocks.
    """

    # Override the elements dictionary to use TransformingCodeBlock.
    elements = dict(Markdown.elements)
    elements["fence"] = TransformingCodeBlock
    elements["code_block"] = TransformingCodeBlock

    def __init__(self, markup: str, code_transform: Transform | None = None, **kwargs) -> None:
        super().__init__(markup, **kwargs)
        self.code_transform = code_transform  # Store the transform function.


_comment_char_regex = re.compile(r"^\s*(#|//|/\*)")


def is_comment(line: str) -> bool:
    return _comment_char_regex.match(line) is not None


def clickable_code(code: str) -> Text:
    """
    Insert Kyrm links into the code.
    """
    kyrm_codes_enabled = global_settings().use_kyrm_codes

    lines: list[str] = code.splitlines()
    texts: list[Text] = []
    for i, line in enumerate(lines):
        if is_comment(line):
            texts.append(Text(line, style=COLOR_COMMENT))
        else:
            if kyrm_codes_enabled:
                kri = Kri(
                    attrs=TextAttrs(
                        hover=TextTooltip(text="Click to paste"),
                        click=UIAction(action_type=UIActionType.paste_text),
                    )
                )
                link = KriLink(kri=kri, link_text=line)
                texts.append(Text.from_ansi(link.as_osc8(), style=STYLE_CODE))
            else:
                texts.append(Text(line, style=STYLE_CODE))

    return Text("\n").join(texts)


class KyrmMarkdown(TransformingMarkdown):
    """
    A Markdown instance that renders as usual, but with added Kyrm codes.
    Currently just to make code lines clickable.
    """

    def __init__(self, markup: str, **kwargs) -> None:
        super().__init__(markup, code_transform=clickable_code, **kwargs)


## Tests


def test_custom_markdown():
    markdown_text = dedent(
        """
        Testing
        ```python
        def hello():
            print("world")
        ```
        """
    )

    def uppercase_code(code: str) -> Text:
        return Text(code.upper())

    md = TransformingMarkdown(markdown_text, code_transform=uppercase_code)

    console = Console(force_terminal=False)
    with console.capture() as capture:
        console.print(md)
    result = [line.rstrip() for line in capture.get().splitlines()]

    expected = [
        "Testing",
        "",
        "",
        "DEF HELLO():",
        '    PRINT("WORLD")',
        "",
    ]

    print(f"\nresult: {result}")
    print(f"\nexpected: {expected}")

    assert result == expected
