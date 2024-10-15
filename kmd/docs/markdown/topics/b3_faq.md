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
Ask by typing any quesion ending in `?` The Kmd assistant knows the docs and can answer many
questions!

Remember there are tab completions on many commands and actions, and that can help you get
started.
You can also try `sugg

Type `?` and press tab to see some frequently asked questions.

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
