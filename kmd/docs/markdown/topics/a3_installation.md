## Installation

### Running the Kmd Shell

The best way to use Kmd is as its own shell, which is a shell environment based on
[xonsh](https://xon.sh/). If you've used a bash or Python shell before, xonsh is very
intuitive.
If you don't want to use xonsh, you can still use it from other shells or as a Python
library.

Within the Kmd shell, you get a full environment with all actions and commands.
You also get intelligent auto-complete and a built-in assistant to help you perform tasks.

### Python and Tool Dependencies

These are needed to run:

- Python 3.11+

- Poetry

- `ffmpeg` (for video conversions), `ripgrep` (for search), `bat` (for prettier file
  display), `imagemagick` (for image display in modern terminals), `libmagic` (for file type
  detection)

Cheat sheets to get these set up, if you're not already:

For macOS, I recommend using brew:

```shell
# Install pyenv, pipx, and other tools:
brew update
brew install pyenv pipx ffmpeg ripgrep bat imagemagick libmagic
```

For Ubuntu:

```shell
# Install pyenv and other tools:
curl https://pyenv.run | bash
apt install pipx ffmpeg ripgrep bat imagemagick libmagic
```

Now install a recent Python and Poetry:

```shell
pyenv install 3.12.7  # Or any version 3.11+ should work.
pipx install poetry
poetry self add "poetry-dynamic-versioning[plugin]"  # Helps build versioning.
```

For Windows or other platforms, see the pyenv and poetry instructions.

### Building

1. [Fork](https://github.com/jlevy/kmd/fork) this repo (having your own fork will make it
   easier to contribute actions, add models, etc.).

2. [Check out](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
   the code.

3. Install the package dependencies:

   ```shell
   poetry install
   ```

### API Key Setup

You will need API keys for all services you wish to use.
Configuring OpenAI, Anthropic, Groq (for Llama 3), Deepgram (for transcriptions), Firecrawl
(for web crawling and scraping), and Exa (for web search) are recommended.

These keys should go in the `.env` file in your current directory.

```shell
# Set up API secrets:
cp .env.template .env 
# Now edit the .env file to add all desired API keys
```

### Running

To run:

```shell
poetry run kmd
```

Use the `check_tools` command to confirm tools like `bat` and `ffmpeg` are found.

Optionally, to install Kmd globally in the current user's Python virtual environment so you
can conveniently use `kmd` anywhere, make sure you have a usable Python 3.12+ environment
active (such as using `pyenv`), then:

```shell
./install_local.sh
```

If you encounter installation issues, you can also try `./install_local.sh
--force-reinstall`.

This does a pip install of the wheel so you can run it as `kmd`.

### Other Ways to Run Kmd

If desired, you can also run Kmd directly from your regular shell, by giving a Kmd shell
command.

```
# Transcribe a video and summarize it:
mkdir myworkspace.kb
cd myworkspace.kb
kmd transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'
```
