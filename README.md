# kmd

A command line for knowledge exploration.

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
# Plugin to help with upgrades:
poetry self add poetry-plugin-up
```

## Before Running

The `.env` file in your current directory must hold needed API keys for all
needed services. Configuring at least OpenAI, Deepgram, Anthropic, and Groq
(for Llama 3) is recommended.

```
# Set up API secrets:
cp .env.template .env 
vi .env # Edit the file to add all desired API keys
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
poetry run kmd

# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'

# A transcription with multiple speakers:
transcribe_video 'https://www.youtube.com/watch?v=uUd7LleJuqM'
# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
break_into_paragraphs
summarize_as_bullets
create_pdf

# Get all videos on a channel and then download and transcribe them:
list_channel_videos 'https://www.youtube.com/@Kboges'
transcribe_video

# Processing a really long document with sliding windows:
transcribe_video 'https://www.youtube.com/watch?v=juD99_sPWGU'
strip_html
break_into_paragraphs
summarize_as_bullets

# Combine all the above into combo and sequence actions:
transcribe_and_format_video_with_description 'https://www.youtube.com/watch?v=XRQnWomofIY'
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
# Just one file, with outputs:
pytest -s kmd/text_docs/text_doc.py

# Upgrade packages:
poetry up

# Poetry update:
poetry self update
```
