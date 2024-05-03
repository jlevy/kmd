# kmd

A command line for knowledge exploration.

## Dev setup

For MacOS:

```
# Install pyenv if needed:
brew update
brew install pyenv
# Install recent Python if needed:
pyenv install 3.12.2
# Install recent Poetry if needed:
curl -sSL https://install.python-poetry.org | python3 -
# Install packages:
poetry install
# Set up API secrets:
cp secrets/secrets.template.toml secrets/secrets.toml  
vi secrets/secrets.toml  # Enter API keys
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
