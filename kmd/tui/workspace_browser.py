import logging
from rich.syntax import Syntax
from rich.traceback import Traceback

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Vertical, Horizontal
from textual.reactive import var
from textual.widgets import DirectoryTree, Footer, Static, Markdown, Input, Footer, Label


from kmd.config import WORKSPACE_DIR
from kmd.file_storage.frontmatter_format import fmf_read

log = logging.getLogger(__name__)

# TODO: Autocomplete
# from kmd.actions.registry import load_all_actions
# from .autocomplete import AutoComplete, DropdownItem, Dropdown, InputState

# commands = [(name, "") for (name, action) in load_all_actions().items()]

# dropdown_items = [DropdownItem(command, "", description) for command, description in commands]


# def command_completions(input_state: InputState) -> list[DropdownItem]:
#     items = []

#     # Match on first word only for now.
#     if len(input_state.value.split()) != 1:
#         return items

#     lookup_str = input_state.value.lower()

#     for command, description in commands:
#         items.append(
#             DropdownItem(
#                 command,
#                 "",
#                 Text(description, style="#c595ed"),
#             )
#         )

#     # Only keep items that contain the Input value as a substring
#     matches = [c for c in items if lookup_str in c.main.plain.lower()]
#     # Favour items that start with the Input value, pull them to the top
#     ordered = sorted(matches, key=lambda v: v.main.plain.startswith(lookup_str))

#     return ordered


class WorkspaceBrowser(App):
    """UI to run commands and see workspace files."""

    CSS_PATH = "workspace_browser.scss"

    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("v", "toggle_content", "Toggle Content View"),
        ("q", "quit", "Quit"),
    ]

    path = WORKSPACE_DIR

    show_tree = var(True)
    show_content = var(False)

    def compose(self) -> ComposeResult:
        """Compose our UI."""

        # yield Header()
        with Horizontal():
            with Vertical():
                yield Container(
                    Label("Command", id="lead-text"),
                    # AutoComplete(
                    #     Input(id="search-box", placeholder="Command..."),
                    #     Dropdown(
                    #         items=command_completions,
                    #         id="my-dropdown",
                    #     ),
                    # ),
                    # id="search-container",
                    Input(id="command-box", placeholder="Command..."),
                )
                yield Static(id="output", expand=True)
            with Container():
                yield DirectoryTree("./workspace", id="tree-view")
                with VerticalScroll(id="content-view"):
                    yield Static(id="file-text", expand=True)
                    yield Markdown(id="file-markdown")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command-box", Input).focus()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""

        event.stop()

        text_view = self.query_one("#file-text", Static)
        markdown_view = self.query_one("#file-markdown", Markdown)

        is_markdown = event.path.suffix == ".md"

        text_syntax = ""
        markdown = ""

        try:
            if is_markdown:
                markdown, _metadata = fmf_read(event.path)
            else:
                text_syntax = Syntax.from_path(
                    str(event.path),
                    line_numbers=False,
                    word_wrap=False,
                    indent_guides=True,
                    theme="github-dark",
                )
        except UnicodeDecodeError:
            log.info("Ignoring UnicodeDecodeError on binary file: %s", event.path)
        except Exception:
            text_view.update(Traceback(theme="github-dark", width=None))
            self.sub_title = "ERROR"
        else:
            text_view.update(text_syntax)
            self.query_one("#file-text").scroll_home(animate=False)

            markdown_view.update(markdown)
            self.query_one("#file-markdown").scroll_home(animate=False)

            self.show_content = True
            self.sub_title = str(event.path)

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""

        self.set_class(show_tree, "-show-tree")

    def watch_show_content(self, show_content: bool) -> None:
        """Called when show_content is modified."""

        self.set_class(show_content, "-show-content")

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""

        self.show_tree = not self.show_tree

    def action_toggle_content(self) -> None:
        """Called in response to key binding."""

        self.show_content = not self.show_content


if __name__ == "__main__":
    WorkspaceBrowser().run()
