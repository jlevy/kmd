## Is Kmd Mature?

No. Not at all. :) It's the result of a few weeks of coding and experimentation, and it's
very much in progress.
Please help me make it better by sharing your ideas and feedback!
It's easiest to DM me at [twitter.com/ojoshe](https://x.com/ojoshe).
My contact info is at [github.com/jlevy](https://github.com/jlevy).

Some of this may be a little crazy or ambitious.
See more motivation in the philosophy section below.

## What is Included?

- A bash-like, Python-compatible shell based on xonsh, with pretty syntax coloring of
  commands and outputs

- Tab auto-completion and help on almost everything

- A [generalized frontmatter format](https://github.com/jlevy/frontmatter-format), that for
  YAML metadata on Markdown, HTML, Python, and other text files

- A [data model](https://github.com/jlevy/kmd/tree/main/kmd/model) that includes items such
  as documents, resources, concepts, etc., all stored as files within a workspace of files,
  and with consistent metadata in YAML on text files

- A few dozen built-in commands for listing, showing, and paging through files, etc.
  (see `help` for full docs)

- An extensible set of actions for all kinds of tasks like editing or summarizing text or
  transcribing videos (see `help`)

- A way of tracking the provenance of each file (what actions created each item) so you can
  tell when to skip running a command (like a Makefile)

- A selection system for maintaining context between commands so you can pass outputs of one
  action into the inputs of another command (this is a bit like pipes but more flexible for
  sequences of tasks, possibly with many intermediate inputs and outputs)

- A set of preconditions, like whether a document is Markdown or HTML, if it's a transcript
  with timestamps, and so on, so you and Kmd know what actions might apply to any selection

- A media cache, which is a mechanism for downloading and caching, downsampling, and
  transcribing video, audio, using Whisper or Deepgram

- A content cache, for downloading and caching web pages or other files

- An LLM-based assistant that wraps the docs and the Kmd source code into a tool that
  assists you in using or extending Kmd (this part is quite fun!)

- A
  [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently

- If your terminal supports it, some major enhancements to the terminal experience:

  - Sixel graphics support (see images right in the terminal)

  - A local server for serving information on files as web pages that can be accessed as OSC
    8 links

  - Sadly, we may have mind-boggling AI tools, but Terminals are still incredibly archaic
    and don't support these features well (more on this below) but I have a new terminal,
    Kyrm, that shows these as tooltips and makes every command clickable (please contact me
    if you'd like an early developer preview, as I'd love feedback)

- A bunch of other small utilities for making all this easier, including:

  - Parsing and representing text docs as sentences, paragraphs, or chunks of text

  - Diffing words and tokens and filtering diffs to control what changes LLMs make to text

  - Tools for detecting file types and automatic, readable file naming conventions

  - Media handling of videos and audio, including downloading and transcribing videos

### Credits

All of this is only possible by relying on a wide variety of powerful libraries, especially
[LiteLLM](https://github.com/BerriAI/litellm), [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Pydantic](https://github.com/pydantic/pydantic),
[Rich](https://github.com/Textualize/rich),
[Ripgrep](https://github.com/BurntSushi/ripgrep), [Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint),
[Marko](https://github.com/frostming/marko), and [Xonsh](https://github.com/xonsh/xonsh).
