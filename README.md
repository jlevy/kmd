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

## Running from Source

Check out code and install package dependencies:

```
# Install packages:
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

To run:

```
poetry run kmd
```

## Installation

To install kmd globally in current user's Python virtual environment (so you can more
conveniently use `kmd` anywhere, make sure you have a usable Python 3.12+ environment
active (such as using `pyenv`), then:

```
./install_local.sh
```

This does a pip install of the wheel so you can run it as `kmd`.

There aren't official pre-built releases yet.

## Using kmd

Use `kmd_help` within the shell for full documentation. Some brief examples:

```
# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe_media 'https://www.youtube.com/watch?v=XRQnWomofIY'

# A transcription with multiple speakers:
transcribe_media 'https://www.youtube.com/watch?v=uUd7LleJuqM'
# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
break_into_paragraphs
summarize_as_bullets
create_pdf

# Get all videos on a channel and then download and transcribe them:
list_channel_items 'https://www.youtube.com/@Kboges'
transcribe_media

# Processing a really long document with sliding windows:
transcribe_media 'https://www.youtube.com/watch?v=juD99_sPWGU'
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
kmd transcribe_media 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

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
