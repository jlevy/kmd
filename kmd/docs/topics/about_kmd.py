"""
Kmd is an extensible command-line tool for exploring and organizing knowledge.
It includes tasks like editing and summarizing text, transcribing videos,
generating PDFs or webpages, and more.

As with the Unix shell, the philosophy is to have simple commands that can be
combined flexibly in complex and powerful ways. Inputs and outputs of commands
are stored as files, so you can easily chain commands together and inspect
intermediate results. When possible, actions are nondestructive and
idempotent—that is, they will either create new files or simply skip an
operation if it's already complete. Some slow actions (like downloading and
transcribing videos) automatically produce cached outputs (stored in the
`kmd_cache` directory) to make things faster.

Kmd is built on top of xonsh, a Python-powered shell language. Most things are
invoked via kmd commands and kmd actions, but you also have access to the full
power of Python and the shell when needed.

On top of this, kmd understands its own code and APIs and can help you use and
even extend it. At any time you can ask a question and have the LLM-based assistant
help you in how to use kmd. Anything you type that ends in a `?` is sent to the
assistant.

Kmd operates on “items”, which are URLs, files, text or Markdown notes, or other
documents. These are stored as simple files, in a single directory, called a
“workspace”. Typically, you want a workspace for a single topic or project. By
convention, workspace directories should have a `.kb` suffix, such as
`fitness.kb`.

Within a workspace, files are organized into folders by type, including
resources, notes, configs, and exports. Most text items are stored in Markdown
format with YAML front matter (the same format used by Jekyll or other static
site generators). Actions can produce export items in any other format, like a
PDF or a webpage.

All items have a “source path”, which is simply the path of the file relative to
the workspace directory. Item files are named in a simple and readable way, that
reflects the title of the item, its type, its format, and in some cases its
provenance. For example,
`notes/day_1_workout_introduction_youtube_transcription_timestamps.note.md` is
an item that is a note (a text file) that is transcription of a YouTube video,
including timestamps, in Markdown format.

The path (directory and filename) each file is simply a convenient locator for
the item. The metadata on text items is in YAML metadata at the top of each
file. The metadata on items includes titles and item types, as you might expect,
but also provenance information, e.g. the URL where a page was downloaded from.
If an item is based on one or more other items (such as a summary that is based
on an original document), the sources are listed in a `derived_from` array
within the `relations` metadata. This means actions can find citations or other
data on the provenance of a given piece of information.

Kmd actions are a set of operations that can operate on one or more items and
produce one or more new items. Actions can invoke APIs, use LLMs, or perform
any other operation that's scriptable in Python. You specify inputs to actions
as URLs or source paths.

URLs that are provided as input and the output of actions are automatically
stored as new items in the workspace. URLs or resources can be added manually,
but this is normally not necessary.

Actions can be chained together in convenient ways. The output of any command is
always marked as the current “selection”, which is then automatically available
for input on a subsequent command. This is sort of like Unix pipes, but is more
convenient and incremental, and allows you to sequence actions, multiple output
items becoming the input of another action.

Kmd makes a few kinds of messy text manipulations easier:

- Reusable LLM actions: A common kind of action is to invoke an LLM (like
  GPT-4o) on a text item, with a given system and user prompt template. New LLM
  actions can be added with a few lines of Python by calling the
  `define_llm_action()` function.

- Sliding window transformations: LLMs can have trouble processing large inputs,
  not just because of context window and because they may make more mistakes
  when making lots of changes at once. Kmd supports running actions in a sliding
  window across the document, then stitching the results back together when
  done.

- Checking and enforcing changes: LLMs do not reliably do what they are asked to
  do. So a key part of making them useful is to save outputs at each step of the
  way and have a way to review their outputs or provide guardrails on what they
  can do with content.

- Fine-grainded diffs with word tokens:  Documents can be represented at the
  word level, using “word tokens” to represent words and normalized whitespace
  (word, sentence, and paragraph breaks, but not line breaks). This allows diffs
  of similar documents regardless of formatting. For example, it is possible to
  ask an LLM only to add paragraph breaks, then drop any other changes it makes
  to other words. You can use this intelligent matching of words to “backfill”
  specific  content from one doc into an edited document, such as pulling
  timestamps from a full transcript back into an edited transcript or summary.

- Paragraph and sentence operations: A lot of operations within actions should
  be done in chunks at the paragraph or sentence level. Kmd offers simple tools
  to subdivide documents into paragraphs and sentences and these can be used
  together with sliding windows to process large documents.

In addition, there are built-in kmd commands that are part of the kmd tool
itself. These allow you to list items in the workspace, see or change the
current selection, archive items, view logs, etc.
"""