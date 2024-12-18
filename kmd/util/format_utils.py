import html
import shlex
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import indent
from typing import Any, Iterable, Optional

import humanfriendly
import regex
from humanize import naturalsize
from inflect import engine

from kmd.util.lazyobject import lazyobject
from kmd.util.strif import abbreviate_str


@lazyobject
def inflect():
    return engine()


def plaintext_to_html(text: str):
    """
    Convert plaintext to HTML, also handling newlines and whitespace.
    """
    return (
        html.escape(text)
        .replace("\n", "<br>")
        .replace("\t", "&nbsp;" * 4)
        .replace("  ", "&nbsp;&nbsp;")
    )


def html_to_plaintext(text: str):
    """
    Convert HTML to plaintext, stripping tags and converting entities.
    """
    text = regex.sub(r"<br>", "\n", text, flags=regex.IGNORECASE)
    text = regex.sub(r"<p>", "\n\n", text, flags=regex.IGNORECASE)
    unescaped_text = html.unescape(text)
    clean_text = regex.sub("<[^<]+?>", "", unescaped_text)
    return clean_text


def fmt_lines(values: Iterable[Any], prefix: str = "    ", line_break: str = "\n") -> str:
    """
    Simple indented or prefixed formatting of values one per line.
    """
    return indent(line_break.join(str(value) for value in values), prefix).rstrip()


def single_line(text: str) -> str:
    """
    Convert newlines and other whitespace to spaces.
    """
    return regex.sub(r"\s+", " ", text).strip()


def clean_up_title(text: str) -> str:
    """
    Clean up arbitrary text to make it suitable for a title. Convert all whitespace to spaces.
    Only allows the most common punctuation, letters, and numbers, but not Markdown, code
    characters etc.
    """
    return regex.sub(r"[^\p{L}\p{N},./:;'!?/@%&()+“”‘’…–—-]+", " ", text).strip()


def _trim_trailing_punctuation(text: str) -> str:
    return regex.sub(r"[.,;:!?]+$", "", text)


def abbreviate_on_words(text: str, max_len: int, indicator: str = "…") -> str:
    """
    Abbreviate text to a maximum length, breaking on whole words (unless the first word
    is too long). For aesthetics, removes trailing punctuation from the last word.
    """
    if len(text) <= max_len:
        return text
    words = text.split()

    if words and max_len and len(words[0]) > max_len:
        return abbreviate_str(words[0], max_len, indicator)

    while words and len(_trim_trailing_punctuation(" ".join(words))) + len(indicator) > max_len:
        words.pop()

    return _trim_trailing_punctuation(" ".join(words)) + indicator


def abbreviate_phrase_in_middle(
    phrase: str, max_len: int, ellipsis="…", max_trailing_len: int = 0
) -> str:
    """
    Abbreviate a phrase to a maximum length, preserving the first and last few words of
    the phrase whenever possible. The ellipsis is inserted in the middle of the phrase.
    """
    if not max_trailing_len:
        max_trailing_len = min(int(max_len / 2), max(16, int(max_len / 4)))

    phrase = " ".join(phrase.split())

    if len(phrase) <= max_len:
        return phrase

    if max_len <= len(ellipsis):
        return ellipsis

    words = phrase.split()
    prefix_tally = 0
    prefix_end_index = 0

    # Walk through the split words, and tally total number of chars as we go.
    for i in range(len(words)):
        words[i] = abbreviate_str(words[i], max_len, ellipsis)
        if prefix_tally + len(words[i]) + len(ellipsis) + max_trailing_len >= max_len and i > 0:
            prefix_end_index = i
            break
        prefix_tally += len(words[i]) + 1

    prefix_end_index = max(1, prefix_end_index)

    # Calculate the start index for the trailing part.
    suffix_start_index = len(words) - 1
    suffix_tally = 0
    for i in range(len(words) - 1, prefix_end_index - 1, -1):
        if suffix_tally + len(words[i]) + len(ellipsis) + prefix_tally > max_len:
            suffix_start_index = i + 1
            break
        suffix_tally += len(words[i]) + 1

    # Replace the middle part with ellipsis.
    words = words[:prefix_end_index] + [ellipsis] + words[suffix_start_index:]

    result = " ".join(word for word in words if word)

    return result


## Some generic formatters that can safely be used for any paths, phrases, timestamps, etc.


def fmt_path(path: str | Path, resolve: bool = True) -> str:
    """
    Format a path or filename for display. This quotes it if it contains whitespace.

    :param resolve: If true paths are resolved. If they are within the current working
    directory, they are formatted as relative. Otherwise, they are formatted as absolute.
    """
    if resolve:
        path = Path(path).resolve()
        cwd = Path.cwd().resolve()
        if path.is_relative_to(cwd):
            path = path.relative_to(cwd)
    else:
        path = Path(path)

    return shlex.quote(str(path))


def fmt_words(*words: str | None, sep: str = " ") -> str:
    """
    Format a list of words or phrases into a single string, with no leading or trailing
    whitespace. Empty or None values are ignored. Other whitespace including \n and \t are
    preserved. Spaces are trimmed only when they would yield a double space due to
    a separator.

    Example usage:
    ```
    fmt_words("Hello", "world!") == "Hello world!"
    fmt_words("Hello ", "world!") == "Hello world!"
    fmt_words("Hello", " world!") == "Hello world!"
    fmt_words("Hello", None, "world!") == "Hello world!"
    fmt_words("Hello", "", "world!") == "Hello world!"
    fmt_words("Hello", " ", "world!") == "Hello world!"
    fmt_words("\nHello\n", "world!\n") == "\nHello\n world!\n"
    fmt_words("Hello", " ", "world!", sep="|") == "Hello| |world!"
    fmt_words("Hello", "John ", "world!", sep=", ") == "Hello, John, world!"
    ```
    """
    # Filter out Nones and empty strings.
    word_list = [word for word in words if word]

    if not word_list:
        return ""

    processed_words = []

    sep_starts_with_space = sep.startswith(" ")
    sep_ends_with_space = sep.endswith(" ")

    for i, word in enumerate(word_list):
        # Avoid double spaces caused by the separator.
        if i > 0 and sep_ends_with_space:
            word = word.lstrip(" ")
        if i < len(word_list) - 1 and sep_starts_with_space:
            word = word.rstrip(" ")
        # If word is now empty, we can skip it.
        if not word:
            continue

        processed_words.append(word)

    return sep.join(processed_words)


def fmt_paras(*paras: str | None, sep: str = "\n\n") -> str:
    """
    Format text as a list of paragraphs, omitting None or empty paragraphs.
    """
    filtered_paras = [para.strip() for para in paras if para is not None]
    return sep.join(para for para in filtered_paras if para)


def fmt_age(since_time: float | timedelta, brief: bool = False) -> str:
    """
    Format a time span as an age, e.g. "2d ago".
    """
    since_time = humanfriendly.coerce_seconds(since_time)
    # Don't log fractions of a second (humanfriendly does this by default).
    since_time = round(since_time)
    if brief:
        agestr = (
            humanfriendly.format_timespan(since_time, detailed=False, max_units=1)
            .replace(" seconds", "s")
            .replace(" second", "s")
            .replace(" minutes", "m")
            .replace(" minute", "m")
            .replace(" hours", "h")
            .replace(" hour", "h")
            .replace(" days", "d")
            .replace(" day", "d")
            .replace(" weeks", "w")
            .replace(" week", "w")
            .replace(" months", "mo")
            .replace(" month", "mo")
            .replace(" years", "y")
            .replace(" year", "y")
        )
    else:
        agestr = humanfriendly.format_timespan(since_time, detailed=False, max_units=2)

    return agestr + " ago"


def fmt_time(
    dt: datetime,
    iso_time: bool = True,
    friendly: bool = False,
    brief: bool = False,
    now: Optional[datetime] = None,
) -> str:
    """
    Format a datetime for display in various formats:
    - ISO timestamp (e.g. "2024-03-15T17:23:45Z")
    - Age (e.g. "2d ago")
    - Friendly format (e.g. "March 15, 2024 17:23 UTC")
    """
    if friendly:
        # Format timezone name, handling UTC specially
        tzname = dt.tzname() or "UTC" if dt.tzinfo else "UTC"
        return dt.strftime("%B %d, %Y %H:%M ") + tzname
    if iso_time:
        return dt.isoformat().split(".", 1)[0] + "Z"
    else:
        if not now:
            now = datetime.now(timezone.utc)
        return fmt_age(now.timestamp() - dt.timestamp(), brief=brief)


def fmt_size_human(size: int) -> str:
    """
    Format a size (typically a file size) in bytes as a human-readable string,
    e.g. "1.2MB".
    """
    # gnu is briefer, uses B instead of Bytes.
    return naturalsize(size, gnu=True)


def fmt_size_dual(size: int, human_min: int = 1000000) -> str:
    """
    Format a size in bytes in both exact and human-readable formats, e.g.
    "1200000 bytes (1.2MB)". The human-readable format is included if the size is
    at least `human_min`.
    """
    readable_size_str = ""
    if size >= human_min:
        readable_size = fmt_size_human(size)
        readable_size_str += f" ({readable_size})"
    return f"{size} bytes{readable_size_str}"


def fmt_count_items(count: int, name: str = "item") -> str:
    """
    Format a count and a name as a pluralized phrase, e.g. "1 item" or "2 items".
    """
    return f"{count} {inflect.plural(name, count)}"  # type: ignore


## Tests


def test_plaintext_to_html():
    assert plaintext_to_html("") == ""
    assert plaintext_to_html("Hello, World!") == "Hello, World!"
    assert plaintext_to_html("Hello\n  World!") == "Hello<br>&nbsp;&nbsp;World!"
    assert plaintext_to_html("Hello\tWorld!") == "Hello&nbsp;&nbsp;&nbsp;&nbsp;World!"
    assert plaintext_to_html("<Hello, World!>") == "&lt;Hello, World!&gt;"


def test_html_to_plaintext():
    assert html_to_plaintext("") == ""
    assert html_to_plaintext("<p>Hello, World!</p>") == "\n\nHello, World!"
    assert html_to_plaintext("<br>Hello, World!<br>") == "\nHello, World!\n"
    assert html_to_plaintext("<BR>Hello, World!<BR>") == "\nHello, World!\n"
    assert (
        html_to_plaintext(
            '<p>Hello,<br>World!<br><div>Hello, <span data-id="123">World!</span></div></p>'
        )
        == "\n\nHello,\nWorld!\nHello, World!"
    )


def test_clean_title():
    assert clean_up_title("Hello, World!") == "Hello, World!"
    assert clean_up_title("Hej, Världen!") == "Hej, Världen!"
    assert clean_up_title("你好 世界") == "你好 世界"
    assert clean_up_title("こんにちは、世界") == "こんにちは 世界"
    assert clean_up_title(" *Hello,*  \n\tWorld!  --123@:': ") == "Hello, World! --123@:':"
    assert clean_up_title("<script foo='blah'><p>") == "script foo 'blah' p"


def test_abbreviate_on_words():
    assert abbreviate_on_words("Hello, World!", 5) == "Hell…"
    assert abbreviate_on_words("Hello, World!", 6) == "Hello…"
    assert abbreviate_on_words("Hello, World!", 13) == "Hello, World!"
    assert abbreviate_on_words("Hello, World!", 12) == "Hello…"
    assert abbreviate_on_words("", 2) == ""
    assert abbreviate_on_words("Hello, World!", 0) == "…"
    assert abbreviate_on_words("", 5) == ""
    assert (
        abbreviate_on_words("Supercalifragilisticexpialidocious is a long word", 20)
        == "Supercalifragilisti…"
    )


def test_abbreviate_phrase_in_middle():
    assert abbreviate_phrase_in_middle("Hello, World! This is a test.", 16) == "Hello, … a test."
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 23)
        == "Hello, … This is a test."
    )
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 27)
        == "Hello, … This is a test."
    )
    assert (
        abbreviate_phrase_in_middle("Hello, World! This is a test.", 40)
        == "Hello, World! This is a test."
    )
    assert abbreviate_phrase_in_middle("Hello, World! This is a test.", 10) == "Hello, …"
    assert (
        abbreviate_phrase_in_middle("Supercalifragilisticexpialidocious is a long word", 24)
        == "Supercalifragilisticexp… …"
    )

    assert (
        abbreviate_phrase_in_middle(
            "Your Mindset Matters (transcription) (clean text) (in paragraphs) (with timestamps) (add_description)",
            64,
        )
        == "Your Mindset Matters (transcription) (clean … (add_description)"
    )


def test_fmt_words():
    # Basic cases.
    assert fmt_words("Hello", "world!") == "Hello world!"
    assert fmt_words("Hello ", "world!") == "Hello world!"
    assert fmt_words("Hello", " world!") == "Hello world!"
    assert fmt_words("Hello", None, "world!") == "Hello world!"
    assert fmt_words("Hello", "", "world!") == "Hello world!"
    # More complex cases.
    assert fmt_words("\nHello\n", "world!\n") == "\nHello\n world!\n"
    assert fmt_words("Hello", " ", "world!") == "Hello world!"
    assert fmt_words("Hello", " John and", "world!") == "Hello John and world!"
    assert fmt_words("Hello", " ", "world!", sep="|") == "Hello| |world!"
    assert fmt_words("Hello", "John", "world!", sep=", ") == "Hello, John, world!"
    # Edge cases.
    assert fmt_words() == ""
    assert fmt_words(None, "x", "   ") == "x"
    assert fmt_words("   ") == "   "
    assert fmt_words("Hello\t", "World", sep=" ") == "Hello\t World"
    assert fmt_words("Hello", "\nWorld", sep=" ") == "Hello \nWorld"
    assert fmt_words("Hello", "   ", "World", sep="---") == "Hello---   ---World"
    assert fmt_words("Hello", "World", sep=" | ") == "Hello | World"
    assert fmt_words(" Hello ", " ", " World ") == " Hello World "
