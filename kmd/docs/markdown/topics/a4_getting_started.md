## Getting Started

### Use Tab Completion and Help!

Tab completion is your friend!
Just press tab to get lists of commands and guidance on help from the LLM-based assistant.

You can also ask any question directly in the shell.

Type `help` for the full documentation.

### An Example: Transcribing Videos

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

# And for fun now let's visualize them in 3d (proof of concept, this could
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

### Essential Kmd Commands

Kmd has quite a few basic commands that are easier to use than usual shell commands.
You can always run `help` for a full list, or run any command with the `--help` option to
see more about the command.

A few of the most important commands for managing files and work are these:

- `check_tools` to confirm your Kmd setup has necessary tools (like bat and ffmpeg).

- `files` lists files in one or more paths, with sorting, filtering, and grouping.

- `workspace` to show or select or create a new workspace.
  Initially you work in the "sandbox" workspace but for more real work you'll want to create
  a workspace, which is a directory to hold the files you are working with.

- `select` shows or sets selections, which are the set of files the next command will run
  on, within the current workspace.

- `edit` runs the currently configured editor (based on the `EDITOR` environment variable)
  on any file, or the current selection.

- `show` lets you show the first file in the current selection or any file you wish.
  It auto-detects whether to show the file in the console, the browser, or using a native
  app (like Excel for a .xls file).

- `param` lets you set certain common parameters, such as what LLM to use (if you wish to
  use non-default model or language).

- `logs` to see full logs (typically more detailed than what you see in the console).

- `history` to see recent commands you've run.

- `import_item` to add a resource such as a URL or a file to your local workspace.

The set of actions that do specific useful things is much longer, but a few to be aware of
include:

- `chat` chat with any configured LLM, and save the chat as a chat document.

- `web_search_topic` searches the web using Exa.

- `crawl_webpage` fetches a webpage and scrapes the content as text, using Firecrawl.

- `download_media` downloads video or audio media from any of several services like YouTube
  or Apple Podcasts, using yt-dlp.

- `transcribe` transcribes video or audio as text document, using Deepgram.

- `proofread` proofreads a document, editing it for typos and errors only.

- `describe_briefly` describes the contents of a document in about a paragraph.

- `summarize_as_bullets` summarizes a text document as a bulleted item.

- `break_into_paragraphs` breaks a long block of text into paragraphs.

- `insert_section_headings` inserts section headings into a document, assuming it is a
  document (like a transcript after you've run `break_into_paragraphs`) that has paragraphs
  but no section headers.

- `show_as_webpage` formats Markdown or HTML documents as a nice web page and opens your
  browser to view it.

- `create_pdf` formats Markdown or HTML documents as a PDF.
