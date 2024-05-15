# kmd

A command line for knowledge exploration.

## Dev setup

One-time Python and other dependency setup (this part assumes MacOS):

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
```

One-time API key setup:

```
# Set up API secrets:
cp secrets/secrets.template.toml secrets/secrets.toml  
vi secrets/secrets.toml  # Enter API keys
```

First time running:

```
# Install packages:
poetry install
# Convenience to set up xonsh:
poetry run xonsh_install_kmd
# Check it works:
poetry run kmd
```

Basic usage:

```
# Enter shell.
poetry shell

# Transcribe a video and summarize it.
kmd action transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'
```

Recommended usage: Use as a shell, via [xonsh](https://xon.sh/):

```
# Run kmd within the xonsh shell:
poetry run kmdsh

# Set up a workspace to test things out:
new_workspace fitness
cd workspace.ws

# Now invoke actions directly!
fetch_page 'https://thisappwillgiveyouabs.com/'
transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'
transcribe_video 'https://www.youtube.com/watch?v=uUd7LleJuqM'
break_into_paragraphs notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
summarize_as_bullets notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
create_pdf notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.md
list_channel_videos https://www.youtube.com/@Kboges
```

Other useful dev tasks:

```
# Run pytests:
pytest
pytest -s kmd/commands/command_parser.py

# To install globally in current user's Python environment (so you can use `kmd` anywhere):
poetry build
pip install --user dist/kmd-0.1.0-py3-none-any.whl 
```
