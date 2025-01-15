## Frequently Asked Questions

### What is Kmd?

Kmd is an extensible command-line power tool for exploring and organizing knowledge.

It integrates the models, APIs, and Python libraries with the flexibility and
extensibility of a modern command line interface.

Use it with GPT4o, Claude 3.5, Deepgram, and other tools to transcribe, translate,
summarize, organize, edit, and visualize videos, podcasts, and documents into
beautifully formatted notes.

> "Simple should be simple.
> Complex should be possible."
> — Alan Kay

The philosophy behind Kmd is similar to Unix shell tools: simple commands that can be
combined in flexible and powerful ways.
It operates on "items" such as URLs, files, or Markdown notes within a workspace
directory. These items are processed by a variety of actions.

For more detailed information, you can run `help` to get background and a list of
commands and actions.

### How do I get started using Kmd?

Run `help` to get an overview.

Or use the Kmd assistant to get help.
Ask by typing any question ending in `?` The Kmd assistant knows the docs and can answer
many questions!

Remember there are tab completions on many commands and actions, and that can help you
get started. You can also try `suggest_actions`.

Type `?` and press tab to see some frequently asked questions.

See also: `What are the most important Kmd commands?`

### How does Kmd accept both shell and assistant requests to the LLM with natural language?

By default, if a command is valid shell or Python, Kmd will treat it as a shell command,
using Xonsh's conventions.

Commands that begin with a `?` are automatically considered assistant requests.

As a convenience, if you begin to type more than one word that is not a valid command,
it will auto-detect and type the `?` for you.
You can also press <space> at the beginning of the line, and this will also type the `?`
for you.

By default the assistant uses a fast LLM (see `param` to check which one is set) but you
can use `assist` do make an assistant request using a different LLM if you want more
careful answers or to try a different model.

### Do you need to know Bash to use Kmd?

Right now, it certainly helps, as it is focusing on basic functionality.
But one goal of Kmd is to make it *far* easier for less technical people to explore and
learn a command-line interface.
Give it a try and let me know!

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

### How is Kmd different from other shells like Bash (or Fish or Xonsh)?

Kmd is built directly on top of Xonsh, so it is very much like a regular shell, but has
extra compatibility with Python, like Xonsh.

But it is intended to be used quite differently from a regular shell.

Although nothing stops you from using traditional commands like `df` or `grep`, most
commands you will want to use are Kmd commands that are more powerful.
For example, `files` is easier to use than `ls`.

Kmd also wraps the shell to natively supports natural language so you can ask questions
starting with `?`.

There are other customizations Kmd needs to make to Xonsh, including tab completion to
fit Kmd commands and actions, reading metadata on items, etc.

### Can Kmd replace my regular shell?

While Kmd doesn't aim to completely replace all uses of the shell—for example, that's
hard to do in general for remote use, and people have many constraints, customizations,
and preferences—I've found it's highly useful for a lot of situations.
It is starting to replace bash or zsh for day-to-day local use on my laptop.

Kmd basically wraps xonsh, so you have almost all the functionality of xonsh and Python
for any purpose.

The [official xonsh tutorial](https://xon.sh/tutorial.html) has a good overview of using
xonsh, including the many ways it differs from bash and other shells like fish.

### What are commands and actions in Kmd?

Any command you type on the command-line in Kmd is a command.

Some commands are basic, built-in commands.
The idea is there are relatively few of these, and they do important primitive things
like `select` (select or show selections), `show` (show an item), `files` (list
files—Kmd's better version of `ls`), `workspace` (shows information about the current
workspace), or `logs` (shows the detailed logs for the current workspace).
In Python, built-in commands are defined by simple functions.

But most commands are defined as an *action*. Actions are invoked just like any other
command but have a standard structure: they are assumed to perform an "action" on a set
of items (files of known types) and then save those items, all within an existing
workspace. Actions are defined as a subclass of `Action` in Python.

### Does nvm (Node version manager) work in kmd?

It's hard to get nvm to work well in xonsh, but try [fnm](https://github.com/Schniz/fnm)
instead! It works just as well and kmd supports `fnm` automatically so it auto-detects
and uses fnm to switch or install Node versions for directories with Node projects (i.e.
there is an `.nvmrc`, `.node-version`, or `package.json` file).
