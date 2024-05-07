import logging

from rich.syntax import Syntax
from rich.traceback import Traceback

from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from textual.reactive import var
from textual.widgets import DirectoryTree, Footer, Header, Static

from kmd.config import WORKSPACE_DIR

log = logging.getLogger(__name__)


class WorkspaceBrowser(App):
    """Browse files in the workspace."""

    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("v", "toggle_content", "Toggle Content View"),
        ("q", "quit", "Quit"),
    ]

    path = WORKSPACE_DIR

    show_tree = var(True)

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""

        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""

        yield Header()
        with Container():
            yield DirectoryTree(self.path, id="tree-view")
            with VerticalScroll(id="content-view"):
                yield Static(id="content", expand=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(DirectoryTree).focus()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""

        event.stop()
        content_view = self.query_one("#content", Static)
        try:
            syntax = Syntax.from_path(
                str(event.path),
                line_numbers=False,
                word_wrap=False,
                indent_guides=True,
                theme="github-dark",
            )
        except UnicodeDecodeError:
            log.info("Ignoring UnicodeDecodeError on binary file: %s", event.path)
        except Exception:
            log.exception("Error reading file: %s", event.path)
            content_view.update(Traceback(theme="github-dark", width=None))
            self.sub_title = "ERROR"
        else:
            content_view.update(syntax)
            self.query_one("#content-view").scroll_home(animate=False)
            self.sub_title = str(event.path)

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""

        self.show_tree = not self.show_tree
