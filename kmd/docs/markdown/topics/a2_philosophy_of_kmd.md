## The Philosophy of Kmd

I'd like to give a little motivation for experimenting with Kmd and why I think it's
potentially so useful.
But jump to [examples](#examples) to get an idea of what it can do.
If you just want to try it, jump to [Getting Started](#getting-started)!

## Why Apps Can't Solve All Your Problems

AI has radically changed the way we use software.
With LLMs and other generative AI models, we've seen big improvements in two areas:

1. Powerful general-purpose new AI tools (ChatGPT, Perplexity, etc.)

2. AI-powered features within specific SaaS tools that are built for the problem you want to
   solve, like Notion, Figma, Descript, etc.

While we have these powerful cloud apps, we all know numerous situations where our problems
aren't easily solved or automated with the usual tools like the ChatGPT interface, Notion,
Google Docs, Slack, Excel, and Zapier.

If you want to use any of the newest AI models and APIs for something not supported by an
existing tool, you generally have to design and build it yourself—in Python and/or a
full-stack web app.

We are told how AI is replacing developers—and it's true tools like GitHub Copilot and
Cursor can help you write code much faster.
But building apps that are good enough people will pay them is hard.
And we can't all drop what we're doing and build new apps.

It has long been a rule that once products become widely successful, the curse of
[Conway's Law](https://en.wikipedia.org/wiki/Conway%27s_law) and the complexity of full-stack
apps means many companies won't add many of the specific features you want, or at best are
likely to do it slowly.

In short, in spite of AI tools accelerating software, certain things don't change: we are
waiting for developers, product managers, designers, and entrepreneurs to design and ship
solutions for us.

### Why Do We Need an AI-Native Command Line?

So what does all this have to do with the command line?

Well, the classic Unix-style command line has been the Swiss Army knife for savvy developers
for decades.
(The bash shell, still used widely, was released 35 years ago!)

Like many developers, I love the terminal (I even wrote a popular
[guide on it](https://github.com/jlevy/the-art-of-command-line), with millions of readers).

A fraction of developers do a lot in a terminal because it is the most efficient way to
solve many problems.
But among most normal people, the command line has pretty bad reputation.
This is a fair criticism.
Command-line shells generally still suffer from three big issues:

- Old and arcane commands, full of obscure behaviors that relatively few people remember

- A text-based interface many find confusing or ugly

- No easy, “native” support for modern tools, apps, and APIs (especially LLMs—and using
  `curl` to call OpenAI APIs doesn't count!)

Even worse, command lines haven't gotten much better.
Few companies make money shipping new command-line tooling.
(In the last few years this has slowly starting to change with tools like nushell, fish, and
Warp.)

Nonetheless, for all its faults, there is a uniquely powerful thing about the command line:
With a command line, you can do complex things that were never planned by an app developer, a
designer, or an enterpreneur building a product.

*You* know your problems better than anyone else.
Any tool that lets you solve complex problems yourself, without waiting for engineers and
designers, can radically improve your productivity.

I think it's a good time to revisit this idea.

In a post-LLM world, it should be possible to do more things without so much time and effort
spent (even with the help of LLMs) on coding and UI/UX design.

If we have an idea for a script or a feature or a workflow, we should not have to spend
weeks or months to iterate on web or mobile app design and full-stack engineering just to see
how well it works.

### The Goals of Kmd

That brings us to the principles behind building a new, AI-native shell:

1. **Make simple tasks simple:** Doing a simple thing (like transcribing a video or
   proofreading a document) should be as easy as running a single command (not clicking
   through a dozen menus).
   We should be able to tell someone how to do something simply by telling them the command,
   instead of sharing a complex prompt or a tutorial video on how to use several apps.

2. **Make complex tasks possible:** Highly complex tasks and workflows should be easy to
   assemble (and rerun if they need to be automated) by adding new primitive actions and
   combining primitive actions into more complex workflows.
   You shouldn't need to be a programmer to use any task—but any task should be extensible
   with arbitrary code (written by you and an LLM) when needed.

3. **Augment human skills and judgement:** Many AI agent efforts aim for pure automation.
   But even with powerful LLMs and tools, full automation is rare.
   Invariably, the best results come from human review wherever it's needed—experimenting
   with different models and prompts, looking at what works, focusing expert human attention
   in the right places.
   The most flexible tools augment, not replace, your ability to review and manipulate
   information.
   It should help both very technical users, like developers, as well as less technical but
   sophisticated users who aren't traditional programmers.

4. **Accelerate discovery of the workflows that work best:** We have so many powerful APIs,
   models, libraries, and tools now—but the real bottleneck is in discovering and then
   orchestrating the right workflows with the right inputs, models, prompts, and human
   assistance.
   Anyone should be able to discover new steps and workflows without waiting on engineers or
   designers.

5. **Understand and build on itself:** A truly AI-native programming environment should
   improve itself!
   Kmd can read its own code and docs, assist you with its own commands, and write new Kmd
   actions.
   Better languages and scripting tools can in fact make LLMs smarter, because it allows
   them to solve problems in ways that are simpler and less error prone.

### Key Features

Kmd is an experimental attempt at building the tool I've wanted for a long time, using a
command line as a starting point, and with an initial focus on content-related tasks.

It may be better to call Kmd a “shell” since it is actually evolving into more than a
command line.
It's more like a first step toward an item-based information operating system—an alternate,
more flexible UX and information architecture for tasks that manipulate content.

I hope it becomes the tool you need when you don't know what tool you need.

Some key elements:

- **Operations are simple commands:** Simple tasks run in a simple way, without the need to
  adopt a whole framework.
  This includes working with APIs and cloud-based tools as easily as you work with local
  files.

- **Content is just files:** We run tasks on local files that are in readable, transparent
  file formats compatible with other tools (Markdown, YAML, HTML, PDFs).

- **The shell maintains context:** The framework helps you keep files organized into a
  simple workspace, which is just a directory that has additional caches, logs, and metadata.
  This not only helps you, but means an AI assistant can have full context.

- **Work interactively and incrementally:** Try each step to test things work, then combine
  them in novel, exploratory ways, all interactively from the shell prompt.
  It's easy to pick up where you left off whenever a step goes wrong.
  To help with this, Kmd defaults to having **idempotent operations** and **caching slow
  operations** (like downloading media files or transcribing a video).

- **Automate and script when ready:** Although you want to try tasks interactively, you also
  want there to be a path from initial interactive work to partially or fully automated
  scripts.
  When every atomic task is a command, it's much easier to assemble more complex scripts
  that repeatably do very complex things.

- **Intelligent and extensible:** Most importantly, Kmd understands itself.
  It reads its own code and docs to give you assistance, including at writing new Kmd
  actions.

All of this is only possible by relying on a wide variety of powerful libraries, especially
[LiteLLM](https://github.com/BerriAI/litellm), [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Pydantic](https://github.com/pydantic/pydantic), [Rich](https://github.com/Textualize/rich),
[Ripgrep](https://github.com/BurntSushi/ripgrep), [Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint),
[Marko](https://github.com/frostming/marko), and [Xonsh](https://github.com/xonsh/xonsh).

### Is Kmd Mature?

No. Not at all.
:) It's the result of a few weeks of coding and experimentation, and it's very much in
progress.
Please help me make it better by sharing your ideas and feedback!
It's easiest to DM me at [twitter.com/ojoshe](https://x.com/ojoshe).
My contact info is at [github.com/jlevy](https://github.com/jlevy).

### What is Included?

- A bash-like, Python-compatible shell based on xonsh, with pretty syntax coloring of
  commands and outputs

- Tab auto-completion and help on almost everything

- A
  [generalized frontmatter format](https://github.com/jlevy/kmd/blob/main/kmd/file_formats/frontmatter_format.py),
  a simple format for Markdown, HTML, Python, and other text files that allows YAML metadata
  on any text file

- A [data model](https://github.com/jlevy/kmd/tree/main/kmd/model) that includes items such
  as documents, resources, concepts, etc., all stored as files within a workspace of files,
  and with consistent metadata in YAML on text files

- A few dozen built-in commands for listing, showing, and paging through files, etc.
  (see `help` for full docs)

- An extensible set of actions for all kinds of tasks like editing or summarizing text or
  transcribing videos (see `help`)

- A way of tracking the provenance of each file (what actions created each item) so you can
  tell when to skip running a command (like a Makefile)

- A selection system for maintaining context between commands so you can pass outputs of one
  action into the inputs of another command

- A set of preconditions, like whether a document is Markdown or HTML, if it's a transcript
  with timestamps, and so on, so you and Kmd know what actions might apply to any selection

- A media cache, which is a mechanism for downloading and caching, downsampling, and
  transcribing video, audio, using Whisper or Deepgram

- A content cache, for downloading and caching web pages or other files

- An LLM-based assistant that wraps the docs and the Kmd source code into a tool that
  assists you in using or extending Kmd (this part is quite fun)

- A
  [Markdown auto-formatter](https://github.com/jlevy/kmd/blob/main/kmd/text_formatting/markdown_normalization.py),
  so text documents are saved in a normalized form that can be diffed consistently

- A bunch of other small utilities for making all this easier, including:

  - parsing and representing text docs as sentences, paragraphs, or chunks of text

  - diffing words and tokens and filtering diffs to control what changes LLMs make to text

  - tools for detecting file types and automatic, readable file naming conventions

  - media handling of videos and audio, including downloading and transcribing videos
