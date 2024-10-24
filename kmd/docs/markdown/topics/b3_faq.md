## Frequently Asked Questions

### What is Kmd?

Kmd is an extensible command-line power tool for exploring and organizing knowledge.

It integrates the models, APIs, and Python libraries with the flexibility and extensibility
of a modern command line interface.

Use it with GPT4o, Claude 3.5, Deepgram, and other tools to transcribe, translate,
summarize, organize, edit, and visualize videos, podcasts, and documents into beautifully
formatted notes.

> "Simple should be simple.
> Complex should be possible."
> — Alan Kay

The philosophy behind Kmd is similar to Unix shell tools: simple commands that can be
combined in flexible and powerful ways.
It operates on "items" such as URLs, files, or Markdown notes within a workspace directory.
These items are processed by a variety of actions.

For more detailed information, you can run `help` to get background and a list of commands
and actions.

### How do I get started using Kmd?

Run `help` to get an overview.

Or use the Kmd assistant to get help.
Ask by typing any question ending in `?` The Kmd assistant knows the docs and can answer many
questions!

Remember there are tab completions on many commands and actions, and that can help you get
started.
You can also try `sugg

Type `?` and press tab to see some frequently asked questions.

See also: `What are the most important Kmd commands?`

### What are the most important Kmd commands?

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

- `add_resource` to add a resource such as a URL or a file to your local workspace.

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

### What is the difference between a command and an action in Kmd?

Any command you type on the command-line in Kmd is a command.

Some commands are basic, built-in commands.
The idea is there are relatively few of these, and they do important primitive things like
`select` (select or show selections), `show` (show an item), `files` (list files—Kmd's better
version of `ls`), `workspace` (shows information about the current workspace), or `logs`
(shows the detailed logs for the current workspace).
In Python, built-in commands are defined by simple functions.

But most commands are defined as an *action*. Actions are invoked just like any other
command but have a standard structure: they are assumed to perform an "action" on a set of
items (files of known types) and then save those items, all within an existing workspace.
Actions are defined as a subclass of `Action` in Python.

### What models are available?

You can use Kmd with any APIs or models you like!
By default it uses APIs from OpenAI, Deepgram, and Anthropic.

### How can I transcribe a YouTube video or podcast?

Here is an example of how to transcribe a YouTube video or podcast, then do some
summarization and editing of it.
(Click or copy/paste these commands.)

```shell
# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'

# Take a look at the output:
show

# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
strip_html
break_into_paragraphs
summarize_as_bullets
create_pdf

# Note transcription works with multiple speakers:
transcribe 'https://www.youtube.com/watch?v=uUd7LleJuqM'

# Or all videos on a channel and then download and transcribe them all:
list_channel 'https://www.youtube.com/@Kboges'
transcribe

# Process a really long document (this one is a 3 hour interview) with sliding windows,
# and a sequence action that transcribes, formats, and includes timestamps for each
# paragraph:
transcribe_format 'https://www.youtube.com/watch?v=juD99_sPWGU'

# Now look at these as a web page:
webpage_config
# Edit the config if desired:
edit
# Now generate the webpage:
webpage_generate
# And look at it in the browser:
show

# Combine more actions in a more complex combo action, adding paragraph annotations and headings:
transcribe_annotate_summarize 'https://www.youtube.com/watch?v=XRQnWomofIY'
show_as_webpage
```
