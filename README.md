<div align="center">

<p style="max-width: 400px;">

<br/>

<b>⎪K⎪M⎪D⎪</b>

<b><i>The Knowledge Command Line</i></b>

<b>An intelligent, extensible shell for knowledge tasks.</b>

⛭

“*Simple should be simple.
Complex should be possible.*” —Alan Kay

<br/>

</p>

</div>

## What is kmd?

Kmd (“Knowledge comMand Line”) is a power tool to help you with practical knowledge tasks
and for the exploration of what's possible with the myriad of AI tools we now have.

Kmd makes it easier to use APIs and tools such as **OpenAI GPT-4o and o1**, **Anthropic
Claude 3.5**, **Groq Llama 3.1** (and any others via **LiteLLM**), **Deepgram**,
**LlamaIndex**, **ChromaDB**, and any other Python tools.

Use commands to transcribe videos, summarize and organize transcripts and notes, extract
concepts, check citations, convert notes to PDFs or beautifully formatted HTML, or perform
numerous other content-related tasks.

The goals of Kmd are:

- **Make simple tasks simple:** Doing a simple thing should be as easy as running a single
  command (not clicking through a dozen menus).
  Telling someone how to do something by telling them the command, instead of sharing a Loom
  video or a complex prompt.

- **Make complex tasks possible:** Highly complex tasks and workflows should be easy to
  assemble (and rerun if they need to be automated) by adding new actions and combining them
  with existing actions.
  Almost anything should be extensible.

- **Work well with other tools:** Using this tool shouldn't mean you can't use other tools,
  too.

- **Allow you to iterate quickly on your documents, data, and workflows:** We have so many
  powerful APIs, models, libraries, and tools now—but the real bottleneck is in figuring out
  how to use them in the right ways.
  To do that we need to experiment with practical workflows without waiting for engineers or
  designers (or LLM agents) to build our tools.

- **Be self-reflective:** All of this should make work easier for LLMs too.
  Kmd should understand and enhance itself to better help you.
  With better primitives, we get smarter—and LLMs get smarter, too.

## Why a New Command Line?

It may be better to call Kmd a "shell" since it is actually evolving into far more than a
command line.
It's more like a first step toward an item-based information operating sytem—an alternate,
more flexible UX and information architecture for tasks that manipulate content.

The classic Unix-style command line has been the Swiss Army knife for savvy developers for
decades.

Like many developers, I love the terminal (I even wrote a popular
[guide on it](https://github.com/jlevy/the-art-of-command-line), with millions of readers).
But the command line has limitations.
We've seen improvements to terminals and shells, but they generally still suffer from three
big issues:

- Arcane commands and a confusing interface mean relatively few people feel comfortable
  using the command line

- No easy, “native” support for modern APIs and apps, especially LLMs (curl doesn't count!)

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

## Is Kmd Mature?

No. Not at all.
:) It's the result of a few weeks of coding and experimentation, and it's very much in
progress.
Please help me make it better by sharing your ideas and feedback!

## What is Included?

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

- A few dozen built-in commands for listing, showing and paging through files, etc.
  (see `help` for full docs)

- An extensible set of actions for all kinds of tasks like editing or summarizing text or
  transcribing videos (see `help`)

- A way of tracking the provenance of each file (what actions created each item) so you can
  tell when to skip running a command (like a Makefile)

- A selection system for maintaining context between commands so you can pass outputs of one
  action into the inputs of another command

- A media cache, which is a mechanism for downloading and caching, downsampling, and
  transcribing video, audio, using Whisper or Deepgram

- A content cache, for downloading and caching web pages or other files

- An LLM-based assistant that wraps the docs and the Kmd source code into a tool that
  assists you in using or extending Kmd (this part is quite fun)

- A
  [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently

- A bunch of little utilities for making all this easier, including

  - parsing text docs into sentences and paragraphs

  - diffing words and tokens and filtering diffs to control what changes LLMs make to text

  - tools for detecting file types and naming files in a clear way

  - media handling of videos and audio, including downloading and translating videos

## Running the Kmd Shell

The best way to use Kmd is as its own shell, which is a shell environment based on
[xonsh](https://xon.sh/). If you've used a bash or Python shell before, xonsh is very
intuitive.
If you don't want to use xonsh, you can still use it from other shells or as a Python
library.

Within the Kmd shell you get a full environment with all actions and commands.
You also get intelligent auto-complete and a built-in assistant to help you perform tasks.

## Python and Shell Setup

Ensure you have these set up:

- Python 3.12+

- Poetry

- `ffmpeg`, `ripgrep`, `bat`

I recommend using pyenv to update Python if needed.

Here is the cheat sheet for these installations on macOS. For Linux and Windows, see the
pyenv and poetry instructions.

```shell
# Install pyenv and pipx if needed:
brew update
brew install pyenv pipx

# Install some additional helpful tools.
# ffmpeg is needed for video conversions.
# ripgrep is needed for the search command.
# bat is optional but improves the show and logs commands.
brew install ffmpeg ripgrep bat

# Ensure you are in the source directory (where .python-version is)
# and install recent Python if needed:
pyenv install

# Install recent Poetry if needed:
pipx install poetry
poetry self update  
```

## Building

1. [Fork](https://github.com/jlevy/kmd/fork) this repo (having your own fork will make it
   easier to contribute actions, add models, etc.).

2. [Check out](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
   the code.

3. Install the package dependencies:

   ```shell
   poetry install
   ```

## API Key Setup

You will need API keys for all services you wish to use.
Configuring OpenAI, Anthropic, Groq (for Llama 3), and Deepgram is recommended.

These keys should go in the `.env` file in your current directory.

```shell
# Set up API secrets:
cp .env.template .env 
# Now edit the .env file to add all desired API keys
```

## Running

To run:

```shell
poetry run kmd
```

Use the `check_tools` command to confirm tools like `bat` and `ffmpeg` are found.

Optionally, to install Kmd globally in current user's Python virtual environment so you can
conveniently use `kmd` anywhere, make sure you have a usable Python 3.12+ environment active
(such as using `pyenv`), then:

```shell
./install_local.sh
```

This does a pip install of the wheel so you can run it as `kmd`.

## Using Kmd

Tab completion is your friend!
Just press tab to get lists of commands and guidance on help from the LLM-based assistant.

You can also ask any question directly in the shell.

Type `help` for the full documentation.

The simplest way to illustrate how to use Kmd is by example.
You can go through the commands below a few at a time, trying each one.

For each command below you can use tab completion (which shows information about each
command or option) or run with `--help` to get more details.

```shell
# Check the help page for a full overview:
help

# Confirm kmd is set up correctly with right tools:
check_tools

# The assistant is built into the shell, so you can just ask questions:
how do I set get started with a new workspace?

# Set up a workspace to test things out (we'll use fitness as an example):
workspace fitness

# A short transcription (use this one or pick any video on YouTube):
transcribe 'https://www.youtube.com/watch?v=KLSRg2s3SSY'

# Take a look at the output:
show

# Now manipulate that transcription. Note we are using the outputs
# of each previous command, which are auto-selected as input to each
# subsequent command. You can always run `show` to see the last result.

# Remove the speaker id <span> tags from the transcript.
strip_html
show

# Break the text into paragraphs:
break_into_paragraphs
show

# Look at the paragraphs and (by looking at the document this text
# doc was derived from) infer the timestamps and backfill them, inserting
# timestamped link to the YouTube video at the end of each paragraph.
backfill_timestamps
show

# Render it as a PDF:
create_pdf

# See the PDF:
show

# See all the files we have created so far:
files

# Browse more detailed system logs (for debugging when necessary):
logs

# Note transcription works with multiple speakers, thanks to Deepgram
# diarization. 
transcribe 'https://www.youtube.com/watch?v=_8djNYprRDI'
show

# We can create more advanced commands that combine sequences of actions.
# This command does everything we just did above: transcribe, format,
# and include timestamps for each paragraph.
transcribe_format 'https://www.youtube.com/watch?v=_8djNYprRDI'

# Getting a little fancier, this one adds little paragraph annotations and
# a nicer summary at the top:
transcribe_annotate_summarize 'https://www.youtube.com/watch?v=_8djNYprRDI'

# Time to see it in a prettier form. Let's look at that as a web page:
show_as_webpage

# We can also list all videos on a channel, saving links to each one as
# a resource .yml file:
list_channel 'https://www.youtube.com/@Kboges'

# Look at what we have and transcribe a couple more:
files resources
transcribe resources/quality_first.resource.yml resources/why_we_train.resource.yml

# Another important thing to note is you can process a really long document.
# This one is a 3-hour interview. Kmd uses sliding windows that process a
# group of paragraphs at a time, then stitches the results back together:
transcribe_format 'https://www.youtube.com/watch?v=juD99_sPWGU'

show_as_webpage
```

## Other Ways to Run Kmd

You can also run Kmd directly from your regular shell, by giving a Kmd shell command.

```
# Transcribe a video and summarize it:
mkdir myworkspace.kb
cd myworkspace.kb
kmd transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

## Tips for Use with Other Tools

While not required, these tools can make using Kmd easier or more fun.

### Choosing a Terminal

You can use any favorite terminal to run Kmd, but I recommend trying
[Hyper](https://hyper.is/) with the [Hyper-K](https://github.com/jlevy/hyper-k) plugin.

I tried half a dozen different popular terminals on Mac (Terminal, Warp, Kitty, etc.), and
none were as easy to customize as I'd like.

Hyper-K is a plugin I've written that makes using a tool like Kmd much easier in small ways,
especially by letting you click commands and file paths with the mouse to type them, and by
easily viewing thumbnail images.

### Choosing an Editor

Most any editor will work.
Kmd respects the `EDITOR` environment variable if you use the `edit` command.

### Using on macOS

Kmd calls `open` to open some files, so in general, it's convenient to make sure your
preferred editor is set up for `.yml` and `.md` files.

For convenience, a reminder on how to do this:

- In Finder, pick a `.md` or `.yml` file and hit Cmd-I (or right click and select Get Info).

- Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
  button to have it apply to all files with that extension.

- Repeat with each file type.

### Using with Cursor and VSCode

[Cursor](https://www.cursor.com/) and [VSCode](https://code.visualstudio.com/) work fine out
of the box to edit workspace files in Markdown, HTML, and YAML in Kmd workspaces.

### Using with Zed

[Zed](https://zed.dev/) is another, newer editor that works great out of the box.

### Using with Obsidian

Kmd uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks".

- This makes the line breaks in Kmd's normalized Markdown output work well in Obsidian.

- Some Kmd files also contain HTML in Markdown.
  This works fine, but note that only the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title
  plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and install.

  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in file
    explorer," "Replace shown title in graph," etc.

  - You probably want to keep the "Replace titles in header of leaves" off so you can still
    see original filenames if needed.

  - Now titles are easy to read for all Kmd notes.

### More Command-Line Tools

These aren't directly related to Kmd but are very useful to know about if you wish to have
modern text UIs for your data files.
These can work well with files created by Kmd.

- [**Ranger**](https://github.com/ranger/ranger) is a powerful terminal-based file manager
  that works well with Kmd-generated files.

- [**Visidata**](https://github.com/saulpw/visidata) is a flexible spreadsheet-like
  multitool for tabular data, handy if you are wanting to manipulate tabular data with Kmd
  actions.

## Development

```shell
# Developers should install poetry plugins to help with dev builds and updates:
poetry self add "poetry-dynamic-versioning[plugin]"
poetry self add poetry-plugin-up

# Build wheel:
poetry build

# Run pytests:
poetry run test
# Or within the poetry shell:
pytest   # all tests
pytest -s kmd/text_docs/text_doc.py  # one test, with outputs

# Before committing, be sure to check formatting/linting issues:
poetry run lint

# Upgrade packages:
poetry up

# Poetry update:
poetry self update

# Debugging: See Python stack traces of all threads:
pkill -USR1 kmd
```

<br/>

<div align="center">

⛭

<p style="max-width: 400px;">

“*Civilization advances by extending the number of important operations which we can perform
without thinking about them.*” —Alfred North Whitehead

</p>

</div>
