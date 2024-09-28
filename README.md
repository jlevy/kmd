<div align="center">

<p style="max-width: 400px;">

<br/>

<b>⎪K⎪M⎪D⎪</b>

<b><i>The Knowledge Command Line</i></b>

<b>An intelligent, extensible shell for knowledge tasks.</b>

⛭

“*Simple should be simple. Complex should be possible.*” —Alan Kay

<br/>

</p>

</div>


## What is kmd?

Kmd ("the Knowledge comMand Line") is a power tool to help you with practical
knowledge tasks and for the exploration of what's possible with the myriad
of AI tools we now have.

Kmd makes it easier to use APIs and tools such as **OpenAI GPT-4 and O1**,
**Anthropic Claude 3.5**, **Groq Llama 3** (and others via **LiteLLM**), **Deepgram**,
**LlamaIndex**, **ChromaDB**, and any other Python tools.

Use commands to transcribe videos, summarize and organize transcripts and notes,
extract concepts, check citations, convert notes to PDFs or beautifully formatted HTML,
or perform numerous other content-related tasks.

The goals of Kmd are:

- **Make simple tasks simple:** Doing a simple thing should be as easy as running a single
  command (not clicking through a dozen menus).

- **Make complex tasks possible:** Highly complex tasks and workflows need to be easier
  to assemble (and rerun if they need to be automated).
  Almost anything should be extensible.

- **Work well with other tools:** Using one tool shouldn't mean you can't use other tools,
  too.

- **Help you iterate on your documents, data, and workflows:** We have so
  many powerful APIs, models, libraries, and tools now that the real bottleneck is in
  figuring out how to iterate on practical workflows that help us *actually* be productive.


## Why a New Command Line?

I prefer to call Kmd a "shell" since it is actually evolving into far more than a command
line. It's more like a first step toward an alternate, more powerful UX and framework to
work with information.

The classic Unix-style command line has been the Swiss Army knife for savvy developers for
decades.

Like many developers, I love the terminal (I even wrote a popular
[guide on it](https://github.com/jlevy/the-art-of-command-line), with millions of
readers). But the command line has limitations.
We've seen improvements to terminals and shells, but they generally still suffer from three
big issues:

- Arcane commands and a confusing interface, so few people except developers feel
  comfortable using it

- No “native” support for modern APIs and apps, especially LLMs (curl doesn't count!)

- Even worse, it's painful and hard to improve these problems

On the other hand, we have wonderful and powerful cloud apps, but we all know the
limitations of the ChatGPT interface, Notion, Google Docs, Slack, Excel,
and Zapier. Unfortunately, once these products are successful, the curse of
[Conway's Law](https://en.wikipedia.org/wiki/Conway%27s_law) and the complexity of
full-stack apps very often means they can't or won't add specific features you want.

If we have an idea for a new feature or workflow, we should not have to spend weeks or
months to iterate on web or mobile app design and full-stack engineering
just to see how well it works. In a post-LLM world, it should be possible to do more
things without so much time and effort spent (even with the help of LLMs) on coding and
UI/UX design.

Kmd is an experimental attempt at building the tool I've wanted for a long time,
using a command line as a starting point, and with an initial focus on
content-related tasks.

I hope it becomes the tool you need when you don't know what tool you need.

Some key elements:

- **Operations are simple commands:** Simple tasks should run in a simple way, without the
  need to adopt a whole framework. This includes working with APIs and cloud-based tools
  as easily as you work with local files.

- **Use local files and transparent file formats:** Run tasks locally using clean, simple file
  formats compatible with other tools (Markdown, YAML, HTML, PDFs). 

- **Maintain context:** The framework helps you keep files organized into a simple workspace,
  which is just a directory that has additional caches, logs, and metadata.
  This not only helps you, but means an AI assistant can have full context.

- **Allow interactive and incremental experimentation:** Try each step to test things work,
  then combine them in novel, exploratory ways, all interactively from the shell prompt,
  so it's easy to pick up where you leave off whenever a step goes wrong.
  This means **idempotent operations** and **caching slow operations** (like downloading
  media files or transcribing a video).

- **Intelligent and extensible:** Kmd understands itself.
  It reads its own code and docs to give you assistance, including at writing new Kmd actions.

All of this is only possible by relying on a wide variety of powerful libraries, especially
[yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Rich](https://github.com/Textualize/rich),
[Ripgrep](https://github.com/BurntSushi/ripgrep),
[Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint),
[Marko](https://github.com/frostming/marko), and
[Xonsh](https://github.com/xonsh/xonsh).

## Is Kmd mature?

No. Not at all. :) It's the result of a few weeks of coding and experimentation, and it's
very much in progress. Please help me make it better by sharing your ideas and feedback!

## What is Included?

- A bash-like, Python-compatible shell based on xonsh, with pretty syntax coloring of
  commands and outputs
  
- Tab auto-completion and help on almost everything
  
- A generalized frontmatter format, a simple format for Markdown, HTML, Python, and other text files
  that allows YAML metadata on any text file

- A data model that includes items such as documents, resources, concepts, etc., all stored as files
  within a workspace of files, and with consistent metadata in YAML on text files

- A few dozen built-in commands for listing, showing and paging through files, etc.

- An extensible set of actions for all kinds of tasks like editing or summarizing text or
  transcribing videos

- A way of tracking the provenance of each file (what actions created each item) so
  you can tell when to skip running a command (like a Makefile)

- A selection system for maintaining context between commands so you can pass outputs of one
  action into the inputs of another command
  
- A simple library for downloading and caching, downsampling, and transcribing videos and
  audios using Whisper or Deepgram

- An LLM-based assistant that wraps the docs and the Kmd source code into a tool 
  that assists you in using or extending Kmd (this part is quite fun)

- A bunch of little utilities for managing all this, including

  - parsing text docs into sentences and paragraphs

  - diffing words and tokens and filtering diffs to control what LLMs do with text

  - auto-formatting text and Markdown in a consistent way

  - tools for detecting file types and naming files in a clear way

  - media handling of videos and audio, including downloading and translating videos 

## Running the Kmd Shell

The best way to use Kmd is as its own shell, which is a shell environment based on
[xonsh](https://xon.sh/). If you've used a bash or Python shell before, xonsh is very
intuitive. If you don't want to use xonsh, you can still use it from other shells or as a
Python library.

Within the Kmd shell you get a full environment with all actions and commands. You also get
intelligent auto-complete and a built-in assistant to help you perform tasks.

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

Type `?` or use `help` within the shell for full documentation.

## Examples

A few commands you can try one at a time to see how kmd works:

```shell
# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'

# Take a look at the output:
show

# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
strip_html
break_into_paragraphs
summarize_as_bullets
create_pdf

# Note transcription works with multiple speakers:
transcribe 'https://www.youtube.com/watch?v=uUd7LleJuqM'

# Or all videos on a channel and then download and transcribe them all:
list_channel 'https://www.youtube.com/@Kboges'
transcribe

# Process a really long document (this one is a 3-hour interview) with sliding windows,
# and a sequence action that transcribes, formats, and includes timestamps for each
# paragraph:
transcribe_format 'https://www.youtube.com/watch?v=juD99_sPWGU'

# Now look at these as a web page:
webpage_config
# Edit the config if desired:
edit
# Now generate the webpage:
webpage_generate
# And look at it in the browser:
show

# Combine more actions in a more complex combo action, adding paragraph annotations and concepts:
transcribe_annotate_summarize 'https://www.youtube.com/watch?v=XRQnWomofIY'
webpage_config
webpage_generate
show
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

You can use any favorite terminal to run Kmd, but I recommend trying [Hyper](https://hyper.is/) with the [Hyper-K](https://github.com/jlevy/hyper-k) plugin.

I tried half a dozen different popular terminals on Mac (Terminal, Warp, Kitty, etc.), and none were as easy to customize as I'd like.

Hyper-K is a plugin I've written that makes using a tool like Kmd much easier in small ways,
especially by letting you click commands and file paths with the mouse to type them, and by
easily viewing thumbnail images.

### Choosing an Editor

Most any editor will work.
Kmd respects the `EDITOR` environment variable if you use the `edit` command.

### macOS

Kmd calls `open` to open some files, so in general, it's convenient to make sure your
preferred editor is set up for `.yml` and `.md` files.

For convenience, a reminder on how to do this:

- In Finder, pick a `.md` or `.yml` file and hit Cmd-I (or right click and select Get Info).

- Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
  button to have it apply to all files with that extension.

- Repeat with each file type.

### Cursor and VSCode

[Cursor](https://www.cursor.com/) and [VSCode](https://code.visualstudio.com/) work fine out
of the box to edit workspace files in Markdown, HTML, and YAML in Kmd workspaces.

### Zed

[Zed](https://zed.dev/) is another, newer editor that works great out of the box.

### Obsidian

Kmd uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks".

- This makes the line breaks in Kmd's normalized Markdown output work well in Obsidian.

- Some Kmd files also contain HTML in Markdown.

- This works fine, but note that only the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title
  plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and install.

  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in file
    explorer," "Replace shown title in graph," etc.

  - You probably want to keep the "Replace titles in header of leaves" off so you can still
    see original filenames if needed.

  - Now titles are easy to read for all Kmd notes.

### More Command-Line Tools

These aren't directly related to Kmd but are very useful to know about if you wish
to have modern text UIs for your data files. These can work well with files created
by Kmd.

- [**Ranger**](https://github.com/ranger/ranger) is a powerful terminal-based file manager
  that works well with Kmd-generated files.

- [**Visidata**](https://github.com/saulpw/visidata) is a flexible spreadsheet-like multitool
  for tabular data, handy if you are wanting to manipulate tabular data with Kmd actions.

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

“*Civilization advances by extending the number of important operations
which we can perform without thinking about them.*” —Alfred North Whitehead 

</p>

</div>
