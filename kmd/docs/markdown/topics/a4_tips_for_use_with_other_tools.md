## Tips for Use with Other Tools

While not required, these tools can make using Kmd easier or more fun.

### Choosing a Terminal

You can use any favorite terminal to run Kmd, but I recommend trying
[Hyper](https://hyper.is/) with the [Hyper-K](https://github.com/jlevy/hyper-k) plugin.

I tried half a dozen different popular terminals on Mac (Terminal, Warp, Kitty, etc.), and
none were as easy to customize as I'd like.

Hyper-K is a plugin I've written that makes using a tool like Kmd much easier in small ways,
especially by letting you click commands and file paths with the mouse to type them, and by
easily viewing thumbnail images.

### Choosing an Editor

Most any editor will work.
Kmd respects the `EDITOR` environment variable if you use the `edit` command.

### Using on macOS

Kmd calls `open` to open some files, so in general, it's convenient to make sure your
preferred editor is set up for `.yml` and `.md` files.

For convenience, a reminder on how to do this:

- In Finder, pick a `.md` or `.yml` file and hit Cmd-I (or right-click and select Get Info).

- Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
  button to have it apply to all files with that extension.

- Repeat with each file type.

### Using with Cursor and VSCode

[Cursor](https://www.cursor.com/) and [VSCode](https://code.visualstudio.com/) work fine out
of the box to edit workspace files in Markdown, HTML, and YAML in Kmd workspaces.

### Using with Zed

[Zed](https://zed.dev/) is another, newer editor that works great out of the box.

### Using with Obsidian

Kmd uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks".

- This makes the line breaks in Kmd's normalized Markdown output work well in Obsidian.

- Some Kmd files also contain HTML in Markdown.
  This works fine, but note that only the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title
  plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and install.

  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in file
    explorer," "Replace shown title in graph," etc.

  - You probably want to keep the "Replace titles in header of leaves" off so you can still
    see original filenames if needed.

  - Now titles are easy to read for all Kmd notes.

### More Command-Line Tools

These aren't directly related to Kmd but are very useful to know about if you wish to have
modern text UIs for your data files.
These can work well with files created by Kmd.

- [**Ranger**](https://github.com/ranger/ranger) is a powerful terminal-based file manager
  that works well with Kmd-generated files.

- [**Visidata**](https://github.com/saulpw/visidata) is a flexible spreadsheet-like
  multitool for tabular data, handy if you are wanting to manipulate tabular data with Kmd
  actions.