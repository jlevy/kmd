# kmd

<div align="center">

<p style="max-width: 450px;">

<b>A command-line power tool for knowledge tasks.</b>

<br/>

“*Simple should be simple.
Complex should be possible.*” —Alan Kay

</p>

</div>

## Running the kmd Shell

The best way to use kmd is as its own shell, which a shell environment based on
[xonsh](https://xon.sh/). If you've used a bash or Python shell before, xonsh is very
intuitive.
If you don't want to use xonsh, you can still use it from other shells or as a Python
library.

Within the kmd shell you get a full environment with all actions and commands.
You also get intelligent auto-complete and a built-in assistant to help you perform tasks.

## Python and Shell Setup

Ensure you have these set up:

- Python 3.12+

- Poetry

- `ffmpeg`, `ripgrep`, `bat`

I recommend using pyenv to update Python if needed.

Here is the cheat sheet for these installations on MacOS. For Linux and Windows, see the
pyenv and poetry instructions.

```shell
# Install pyenv and pipx if needed:
brew update
brew install pyenv pipx

# Install some additional helpful.
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
poetry config virtualenvs.in-project true
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

Optionally, to install kmd globally in current user's Python virtual environment so you can
conveniently use `kmd` anywhere, make sure you have a usable Python 3.12+ environment active
(such as using `pyenv`), then:

```shell
./install_local.sh
```

This does a pip install of the wheel so you can run it as `kmd`.

## Using kmd

Tab completion is your friend!
Just press tab to get lists of commands and guidance on help from the LLM-based assistant.

Type `?` or use `kmd_help` within the shell for full documentation.

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

# Process a really long document (this one is a 3 hour interview) with sliding windows,
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

You can also run kmd directly from your regular shell, by giving a kmd shell command.

```
# Transcribe a video and summarize it:
mkdir myworkspace.kb
cd myworkspace.kb
kmd transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

## Tips for Use with Other Tools

While not required, these tools can make using kmd easier or more fun.

### Choosing a Terminal

You can use any favorite terminal to run kmd, but I recommend trying a try to
[Hyper](https://hyper.is/) with the [Hyper-K](https://github.com/jlevy/hyper-k) plugin.

I tried half a dozen different popular terminals on Mac (Terminal, Warp, Kitty, etc.), and
none were as easy to customize as I'd like.

Hyper-K is a plugin I've written that makes using a tool like kmd much easier in small ways,
especially by letting you click commands and file paths with the mouse to type them, and by
easily viewing thumbnail images.

### Choosing an Editor

Most any editor will work.
Kmd respsects the `EDITOR` environment variable if you use the `edit` command.

### MacOS

Kmd calls `open` to open some files, so in general, it's convenient to make sure your
preferred editor is set up for .yml and .md files.

For convenience, a reminder on how to do this:

- In Finder, pick a .md or .yml file and hit Cmd-I (or right click and select Get Info).

- Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
  button to have it apply to all files with that extension.

- Repeat with each file type.

### Cursor and VSCode

[Cursor](https://www.cursor.com/) and [VSCode](https://code.visualstudio.com/) work fine out
of the box to edit workspace files in Markdown, HTML, and YAML in kmd workspaces.

### Zed

[Zed](https://zed.dev/) is another, newer editor that works great out of the box.

### Obsidian

Kmd uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks".

- This makes the line breaks in kmd's normalized Mardown output work well in Obsidian.

- Some kmd files also contain HTML in Markdown.

- This works fine, but note that only the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title
  plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and install.

  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in file
    explorer," "Replace shown title in graph," etc.

  - You probably want to keep the "Replace titles in header of leaves" off so you can still
    see original filenames if needed.

  - Now titles are easy to read for all kmd notes.

### More Command-Line Tools

- [**Ranger**](https://github.com/ranger/ranger) is a powerful terminal-based file manager
  that works well with kmd generated files.

- [**Vizdata**](https://github.com/saulpw/visidata) is a flexible spreadsheet-like multitool
  for tabular data.

## Development

## Development Tasks

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

## Devvelopment Setup

On VSCode or Cursor, the
[µfmt extension](https://marketplace.visualstudio.com/items?itemName=omnilib.ufmt) works
nicely to use both µfmt and black with project settings.
