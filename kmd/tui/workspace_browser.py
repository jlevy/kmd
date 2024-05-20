import sys
from rich.syntax import Syntax
from rich.traceback import Traceback

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Vertical, Horizontal
from textual.reactive import var
from textual.widgets import DirectoryTree, Footer, Static, Markdown, Input, Footer, Label


from kmd.file_storage.frontmatter_format import fmf_read
from kmd.file_storage.workspaces import current_workspace_dir
from kmd.config.logging import get_logger

log = get_logger(__name__)


class WorkspaceBrowser(App):
    """UI to run commands and see workspace files."""

    CSS_PATH = "workspace_browser.scss"

    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("v", "toggle_content", "Toggle Content View"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()

        self.path = current_workspace_dir()

        self.show_tree = var(True)
        self.show_content = var(False)

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


if __name__ == "__main__" and not "pytest" in sys.modules:
    WorkspaceBrowser().run()
