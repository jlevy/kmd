"""
Kmd is an extensible command-line tool for exploring and organizing knowledge.
It includes tasks like editing and summarizing text, transcribing videos,
generating PDFs or webpages, and more.

As with the Unix shell, the philosophy is to have simple commands that can be
combined flexibly in complex and powerful ways. Inputs and outputs of commands
are stored as files, so you can easily chain commands together and inspect
intermediate results. When possible, slow actions produce cached outputs and
most actions are nondestructive and idempotent—that is, they will either create
new files or simply skip an operation if it's already complete.

kmd is built on top of xonsh, a Python-powered shell language. Most things are
invoked via kmd commands and kmd actions, but you also have access to the full
power of Python and the shell when needed.

kmd operates on “items”, which are URLs, files, text or Markdown notes, or other
documents. These are stored as simple files, in a single directory, called a
“workspace”. Typically, you want a workspace for a single topic or project. By
convention workspace directories have a `.kb` suffix, such as `fitness.kb`.

Within a workspace, files are organized into folders by type, including
resources, notes, configs, and exports. Whenever possible, text items are stored
in Markdown format with YAML front matter (the same format used by Jekyll or
other static site generators). Actions can produce export items in any other
format, like a PDF or a webpage.

All items have a “source path”, which is simply the path of the file relative to
the workspace directory. Item files are named in a simple and readable way, that
reflects the title of the item, its type, its format, and in some cases its
provenance. For example,
`notes/day_1_workout_introduction_youtube_transcription_timestamps.note.md` is
an item that is a note (a text file) that is transcription of a YouTube video,
including timestamps, in Markdown format.

The actual name of the file is simply a convenient “handle” for the item, but
the metadata on text items is in YAML metadata at the top of each file.  The
metadata on items includes titles and item types, as you might expect, but also
provenance information, e.g. the URL where a page was downloaded from, or the
item.

kmd actions are a set of actions that can operate on one or more items and
produce new items. Actions can invoke APIs, use LLMs, or perform any other
operation that's scriptable in Python. You specify inputs to actions as URLs or
source paths.

Actions can be chained together in convenient ways. The output of any command is
always stored as a “selection”, which is then automatically available for input
on a subsequent command. This is sort of like Unix pipes, but is more convenient
and incremental, and allows you to sequence actions, multiple output items
becoming the input of another action.

In addition, there are built-in kmd commands that are part of the kmd tool
itself. These allow you to list items in the workspace, see or change the
current selection, archive items, view logs, etc.
"""
