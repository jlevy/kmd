# kmd

A command line for knowledge exploration.

## Python Setup

Ensure you have a modern Python 3.12+ and Poetry (this part assumes MacOS):

```
# Install pyenv if needed:
brew update
brew install pyenv

# Install ffmpeg if needed:
brew install ffmpeg

# Ensure you are in the source directory (where .python-version is)
# and install recent Python if needed:
pyenv install

# Install recent Poetry if needed:
curl -sSL https://install.python-poetry.org | python3 -
# Plugin to help with upgrades:
poetry self add poetry-plugin-up
```

## Before Running

The `secrets.toml` file in your current directory (or a parent directory) must hold
needed API keys for OpenAI, Deepgram, and any other needed services:

```
# Set up API secrets:
cp secrets.template.toml secrets/secrets.toml  
vi secrets.toml  # Enter API keys
```

Install package dependencies:

```
# Install packages:
poetry install
```

## Running the kmd Shell

The recommended way to use kdm is as its own shell, via [xonsh](https://xon.sh/), so you get
a full environment with all actions, completions, and other commands:

```
# Run kmd within the xonsh shell:
poetry run kmdsh

# Set up a workspace to test things out:
workspace fitness

# Now invoke actions directly!
fetch_page 'https://thisappwillgiveyouabs.com/'
# A short transcription:
transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'

# A transcription with multiple speakers:
transcribe_video 'https://www.youtube.com/watch?v=uUd7LleJuqM'
# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
break_into_paragraphs
summarize_as_bullets
create_pdf

# Get all videos on a channel and then download them (to cache), and then transcribe them.
list_channel_videos 'https://www.youtube.com/@Kboges'
transcribe_video
```

## Other Ways to Run kmd

You can also run kmd directly from your regular shell:

```
# Ensure your Python environment is set up:
poetry shell

# Transcribe a video and summarize it:
mkdir myworkspace.kb
cd myworkspace.kb
kmd transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

To install globally in current user's Python environment (so you can use `kmd` anywhere):

```
poetry build
pip install --user dist/kmd-0.1.0-py3-none-any.whl 
```

## Dev Tasks

```
# Run pytests:
pytest
pytest -s kmd/commands/command_parser.py

# Upgrade packages:
poetry up
```
