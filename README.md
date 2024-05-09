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
# Check it works:
poetry run kmd --help
```

Try it out!

```
# Transcribe a video and summarize it.
poetry run kmd action fetch_page 'https://www.investopedia.com/terms/r/risktolerance.asp'
poetry run kmd action transcribe_video 'https://www.youtube.com/watch?v=XRQnWomofIY'
poetry run kmd action break_into_paragraphs notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
poetry run kmd action summarize_as_bullets notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.txt
poetry run kmd action create_pdf notes/the_weighted_pull_up_is_one_of_the_most_effective_upper_body_exe.note.md
```

Other useful testing and development commands:

```
# Run pytests:
poetry run pytest
poetry run pytest -s kmd/commands/command_parser.py

# Run from shell:
poetry shell
python kmd/main.py --help
```

Install globally in current user's Python environment (so you can use `kmd` anywhere):

```
poetry build
pip install --user dist/kmd-0.1.0-py3-none-any.whl 
```