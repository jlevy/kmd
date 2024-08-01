# kmd

A command line for knowledge exploration.

## Running the kmd Shell

Although you can run it as a library or for single commands, the best way to use kmd
is as its own shell, which a shell environment based on [xonsh](https://xon.sh/).

You get a full environment with all actions, completions, and other commands.

## Python Setup

Ensure you have a modern Python 3.12+ and Poetry (this part assumes MacOS):

```
# Install pyenv and pipx if needed:
brew update
brew install pyenv
brew install pipx

# Install ffmpeg:
brew install ffmpeg

# Ensure you are in the source directory (where .python-version is)
# and install recent Python if needed:
pyenv install

# Install recent Poetry if needed:
pipx install poetry
poetry self update

# Optional for devs: Poetry plugins to help with dev builds and updates:
poetry self add "poetry-dynamic-versioning[plugin]"
poetry self add poetry-plugin-up
```

## Building

There aren't pre-built releases yet. Check out the code and install the package dependencies:

```
poetry install
```

## API Key Setup

You will need API keys for all services you wish to use.
Configuring at least OpenAI, Deepgram, Anthropic, and Groq (for Llama 3) is recommended.

These keys should go in the `.env` file in your current directory.

```
# Set up API secrets:
cp .env.template .env 
vi .env # Edit the file to add all desired API keys
```

## Running

To run:

```
poetry run kmd
```

Optionally, to install kmd globally in current user's Python virtual environment (so you can more
conveniently use `kmd` anywhere, make sure you have a usable Python 3.12+ environment
active (such as using `pyenv`), then:

```
./install_local.sh
```

This does a pip install of the wheel so you can run it as `kmd`.

## Using kmd

Use `kmd_help` within the shell for full documentation. Some brief examples:

```
# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'

# A transcription with multiple speakers:
transcribe 'https://www.youtube.com/watch?v=uUd7LleJuqM'
# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
break_into_paragraphs
summarize_as_bullets
create_pdf

# Get all videos on a channel and then download and transcribe them:
list_channel 'https://www.youtube.com/@Kboges'
transcribe

# Processing a really long document with sliding windows:
transcribe 'https://www.youtube.com/watch?v=juD99_sPWGU'
strip_html
break_into_paragraphs
summarize_as_bullets

# Combine all the above into combo and sequence actions:
transcribe_and_format_video_with_description 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

## Other Ways to Run kmd

You can also run kmd directly from your regular shell, by giving a kmd shell
command.

```
# Transcribe a video and summarize it:
mkdir myworkspace.kb
cd myworkspace.kb
kmd transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

## Tips for Use with Other Tools

### MacOS

In general, it's convenient to make sure your preferred editor is set up for
.yml and .md files.

For convenience, a reminder on how to do this:

  - In Finder, pick a .md or .yml file and hit Cmd-I (or right click and select Get Info).
  - Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
    button to have it apply to all files with that extension.
  - Repeat with each file type.

### Obsidian

Kmd uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks". This makes
  the line breaks in kmd's normalized Mardown output work well in Obsidian.

- Some kmd files also contain HTML in Markdown. This works fine, but note that only
  the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and install.
  
  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in file explorer,"
    "Replace shown title in graph," etc. You probably want to keep the "Replace titles in header
    of leaves" off so you can still see original filenames if needed.

  - Now titles are easy to read for all kmd notes.


## Development Tasks

```
# Build wheel:
poetry build

# Run pytests:
pytest
# Just one file, with outputs:
pytest -s kmd/text_docs/text_doc.py

# Upgrade packages:
poetry up

# Poetry update:
poetry self update

# Debugging: See Python stack traces of all threads:
pkill -USR1 -f xonsh
```
