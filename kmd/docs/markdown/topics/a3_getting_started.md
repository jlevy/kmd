## Getting Started

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
  display), `libmagic`

Cheat sheets to get these set up, if you're not already:

For macOS, I recommend using brew:

```shell
# Install pyenv, pipx, and other tools:
brew update
brew install pyenv pipx ffmpeg ripgrep bat libmagic
```

For Ubuntu:

```shell
# Install pyenv and other tools:
curl https://pyenv.run | bash
apt install pipx ffmpeg ripgrep bat libmagic1
```

Now install a recent Python and Poetry:

```shell
pyenv install 3.11.10  # Or any later version, like 3.12.6.
pipx install poetry
poetry self update  
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

## Examples

Tab completion is your friend!
Just press tab to get lists of commands and guidance on help from the LLM-based assistant.

You can also ask any question directly in the shell.

Type `help` for the full documentation.

The simplest way to illustrate how to use Kmd is by example.
You can go through the commands below a few at a time, trying each one.

For each command below you can use tab completion (which shows information about each
command or option) or run with `--help` to get more details.

```shell
# Check the help page for a full overview:
help

# Confirm kmd is set up correctly with right tools:
check_tools

# The assistant is built into the shell, so you can just ask questions:
how do I get started with a new workspace?

# Set up a workspace to test things out (we'll use fitness as an example):
workspace fitness

# A short transcription (use this one or pick any video on YouTube):
transcribe https://www.youtube.com/watch?v=KLSRg2s3SSY

# Take a look at the output:
show

# Now manipulate that transcription. Note we are using the outputs
# of each previous command, which are auto-selected as input to each
# subsequent command. You can always run `show` to see the last result.

# Remove the speaker id <span> tags from the transcript.
strip_html
show

# Break the text into paragraphs:
break_into_paragraphs
show

# Look at the paragraphs and (by following the `derived_from` relation
# this doc up to find the original source) then infer the timestamps
# and backfill them, inserting timestamped link to the YouTube video
# at the end of each paragraph.
backfill_timestamps
show

# Render it as a PDF:
create_pdf

# See the PDF.
show

# Cool. But it would be nice to have some frame captures from the video.
are there any actions to get screen captures from the video?

# Oh yep, there is!
# But we're going to want to run it on the previous doc, not the PDF.
# Let's see what the files were.
files

# And select that file and confirm it looks like it has timestamps.
# (Pick the right name, the one with backfill_timestamps in it.)
select docs/training_for_life_step06_backfill_timestamps.doc.md
show

# Okay let's try it.
insert_frame_captures

# Let's look at that as a web page.
show_as_webpage

# (Note that's a bit of a trick, since that action is running other
# actions that convert the document into a nicer HTML format.)

# What if something isn't working right?
# Sometimes we may want to browse more detailed system logs:
logs

# Note transcription works with multiple speakers, thanks to Deepgram
# diarization. 
transcribe https://www.youtube.com/watch?v=_8djNYprRDI
show

# We can create more advanced commands that combine sequences of actions.
# This command does everything we just did above: transcribe, format,
# and include timestamps for each paragraph.
transcribe_format https://www.youtube.com/watch?v=_8djNYprRDI

# Getting a little fancier, this one adds little paragraph annotations and
# a nicer summary at the top:
transcribe_annotate_summarize https://www.youtube.com/watch?v=_8djNYprRDI

# A few more possibilities...

# Let's now look at the concepts discussed in that video (adjust the filename
# if needed):
find_concepts docs/how_to_train_your_peter_attia_step14_add_description_1.doc.md
show

# And save them as items:
save_concepts

# We now have about 40 concepts. But maybe some are near duplicates (like
# "high intensity interval training" vs "high intensity intervals").
# Let's embed them and find near duplicates:
find_near_duplicates

# In my case I see one near duplicate, which I'll archive:
archive

# And for fun now let's vizualize them in 3d (proof of concept, this could
# get a lot better):
graph_view --concepts_only

# We can also list all videos on a channel, saving links to each one as
# a resource .yml file:
list_channel https://www.youtube.com/@Kboges

# Look at what we have and transcribe a couple more:
files resources
transcribe resources/quality_first.resource.yml resources/why_we_train.resource.yml

# Another interesting note: you can process a really long document.
# This one is a 3-hour interview. Kmd uses sliding windows that process a
# group of paragraphs at a time, then stitches the results back together:
transcribe_format https://www.youtube.com/watch?v=juD99_sPWGU

show_as_webpage
```
