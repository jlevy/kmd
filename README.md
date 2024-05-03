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

API keys:

```
# Set up API secrets:
cp secrets/secrets.template.toml secrets/secrets.toml  
vi secrets/secrets.toml  # Enter API keys
```

Development and running:

```
# Install packages:
poetry install
# Run:
poetry run kmd --help
poetry run kmd transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'
# Install globally in current user's Python environment (so you can use `kmd` anywhere):
poetry build
pip install --user dist/kmd-0.1.0-py3-none-any.whl 
# Use shell for development and testing:
poetry shell
.venv/bin/kmd --help
```
