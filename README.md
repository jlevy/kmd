# kmd

A command line for knowledge exploration.

## Dev setup

One-time Python setup (this part assumes MacOS):

```
# Install pyenv if needed:
brew update
brew install pyenv
# Install recent Python if needed:
pyenv install 3.12.2
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
kmd action fetch_page 'https://www.investopedia.com/terms/r/risktolerance.asp'
kmd action transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'
kmd action break_into_paragraphs notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
kmd action summarize_as_bullets notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
kmd action create_pdf notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.md
```

But it's easier to use in [xonsh](https://xon.sh/):

```
# Run xonsh with kmd activated:
poetry run xonsh

# Now invoke actions directly!
fetch_page 'https://www.investopedia.com/terms/r/risktolerance.asp'
```

Other useful devlopment tasks:

```
# Run pytests:
pytest
pytest -s kmd/commands/command_parser.py

# To install globally in current user's Python environment (so you can use `kmd` anywhere):
poetry build
pip install --user dist/kmd-0.1.0-py3-none-any.whl 
```
