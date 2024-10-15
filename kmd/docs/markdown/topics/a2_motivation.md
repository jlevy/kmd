

## Motivation

I'd like to give a little motivation for experimenting with Kmd and why I think it's
potentially so useful.
But jump to [examples](#examples) to get an idea of what it can do.
If you just want to try it, jump to [Getting Started](#getting-started)!

The goals of Kmd are:

- **Make simple tasks simple:** Doing a simple thing (like transcribing a video or
  proofreading a document) should be as easy as running a single command (not clicking
  through a dozen menus).
  We should be able to tell someone how to do something simply by telling them a command,
  instead of sharing a complex prompt or a tutorial video on how to use several apps.

- **Make complex tasks possible:** Highly complex tasks and workflows should be easy to
  assemble (and rerun if they need to be automated) by adding new primitive actions and
  combining primitive actions into more complex workflows.
  You shouldn't need to be a programmer to use any task—but any task should be extensible
  with arbitrary code (written by you and an LLM) when needed.

- **Augment human skills and judgement:** Some agent-style tools aim for pure automation.
  But even with powerful LLMs and tools, full automation is rare.
  Invariably, the best results come from human review wherever it's needed—experimenting
  with different models and prompts, looking at what works, focusing expert human attention
  in the right places.
  The most flexible tools augment, not replace, your ability to review and manipulate
  information.

- **Accelerate discovery of the workflows that work best:** We have so many powerful APIs,
  models, libraries, and tools now—but the real bottleneck is in discovering and then
  orchestrating the right workflows with the right inputs, models, prompts, and human
  assistance.
  Anyone should be able to discover new steps and workflows without waiting on engineers or
  designers.

- **Understand and build on itself:** Kmd can read its own code and docs and use itself.
  Better languages and scripting tools should make LLMs smarter, by automating and
  orchestraging complex tasks in ways that are more understandable and less error prone.

### Why a New Command Line?

It may be better to call Kmd a “shell” since it is actually evolving into more than a
command line.
It's more like a first step toward an item-based information operating system—an alternate,
more flexible UX and information architecture for tasks that manipulate content.

The classic Unix-style command line has been the Swiss Army knife for savvy developers for
decades.
(The still widely used bash shell was released 35 years ago!)

Like many developers, I love the terminal (I even wrote a popular
[guide on it](https://github.com/jlevy/the-art-of-command-line), with millions of readers).
But the command line has limitations.
We've seen improvements to terminals and shells, but they generally still suffer from three
big issues:

- Arcane commands and a confusing interface mean relatively few people feel comfortable
  using the command line

- No easy, “native” support for modern APIs and apps, especially LLMs (`curl` doesn't
  count!)

- For legacy reasons, it's sadly hard to improve these problems

On the other hand, we have wonderful and powerful cloud apps, but we all know the
limitations of the ChatGPT interface, Notion, Google Docs, Slack, Excel, and Zapier.
Unfortunately, as each of these products has become more successful, the curse of
[Conway's Law](https://en.wikipedia.org/wiki/Conway%27s_law) and the complexity of full-stack
apps means they won't add many of the specific features you want, or at best will do it
slowly.

If we have an idea for a new feature or workflow, we should not have to spend weeks or
months to iterate on web or mobile app design and full-stack engineering just to see how well
it works.
In a post-LLM world, it should be possible to do more things without so much time and effort
spent (even with the help of LLMs) on coding and UI/UX design.

Kmd is an experimental attempt at building the tool I've wanted for a long time, using a
command line as a starting point, and with an initial focus on content-related tasks.

I hope it becomes the tool you need when you don't know what tool you need.

Some key elements:

- **Operations are simple commands:** Simple tasks run in a simple way, without the need to
  adopt a whole framework.
  This includes working with APIs and cloud-based tools as easily as you work with local
  files.

- **Content is just files:** We run tasks on local files that are in readable, transparent
  file formats compatible with other tools (Markdown, YAML, HTML, PDFs).

- **Maintain context:** The framework helps you keep files organized into a simple
  workspace, which is just a directory that has additional caches, logs, and metadata.
  This not only helps you, but means an AI assistant can have full context.

- **Allow interactive and incremental experimentation:** Try each step to test things work,
  then combine them in novel, exploratory ways, all interactively from the shell prompt, so
  it's easy to pick up where you leave off whenever a step goes wrong.
  This means **idempotent operations** and **caching slow operations** (like downloading
  media files or transcribing a video).

- **Intelligent and extensible:** Kmd understands itself.
  It reads its own code and docs to give you assistance, including at writing new Kmd
  actions.

All of this is only possible by relying on a wide variety of powerful libraries, especially
[LiteLLM](https://github.com/BerriAI/litellm), [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Pydantic](https://github.com/pydantic/pydantic), [Rich](https://github.com/Textualize/rich),
[Ripgrep](https://github.com/BurntSushi/ripgrep), [Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint),
[Marko](https://github.com/frostming/marko), and [Xonsh](https://github.com/xonsh/xonsh).

### Is Kmd Mature?

No. Not at all.
:) It's the result of a few weeks of coding and experimentation, and it's very much in
progress.
Please help me make it better by sharing your ideas and feedback!

### What is Included?

- A bash-like, Python-compatible shell based on xonsh, with pretty syntax coloring of
  commands and outputs

- Tab auto-completion and help on almost everything

- A
  [generalized frontmatter format](https://github.com/jlevy/kmd/blob/main/kmd/file_formats/frontmatter_format.py),
  a simple format for Markdown, HTML, Python, and other text files that allows YAML metadata
  on any text file

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
  action into the inputs of another command

- A set of preconditions, like whether a document is Markdown or HTML, if it's a transcript
  with timestamps, and so on, so you and Kmd know what actions might apply to any selection

- A media cache, which is a mechanism for downloading and caching, downsampling, and
  transcribing video, audio, using Whisper or Deepgram

- A content cache, for downloading and caching web pages or other files

- An LLM-based assistant that wraps the docs and the Kmd source code into a tool that
  assists you in using or extending Kmd (this part is quite fun)

- A
  [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently

- A bunch of other small utilities for making all this easier, including:

  - parsing and representing text docs as sentences, paragraphs, or chunks of text

  - diffing words and tokens and filtering diffs to control what changes LLMs make to text

  - tools for detecting file types and automatic, readable file naming conventions

  - media handling of videos and audio, including downloading and transcribing videos

