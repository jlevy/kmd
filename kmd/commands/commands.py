import os
import re
import textwrap
from typing import Callable, List, Optional
from datetime import datetime
import humanize
from rich import print as rprint
from rich.text import Text
from kmd.commands.local_file_tools import open_platform_specific

from kmd.file_storage.workspaces import canon_workspace_name, current_workspace, show_workspace_info
from kmd.model.locators import StorePath
from kmd.util.text_formatting import format_lines, plural
from kmd.config.logger import get_logger

log = get_logger(__name__)


_commands: List[Callable] = []


def register_command(func):
    _commands.append(func)
    return func


def all_commands():
    return sorted(_commands, key=lambda cmd: cmd.__name__)


def command_output(message: str, *args, color="yellow"):
    rprint(Text(message % args, color))


@register_command
def kmd_help() -> None:
    """
    kmd help. Lists all available actions.
    """
    from kmd.actions.action_registry import load_all_actions

    rprint(Text("\nAvailable kmd commands:\n", style="bright_green"))

    def format_doc(name: str, doc: str) -> Text:
        doc = textwrap.dedent(doc).strip()
        wrapped = textwrap.fill(doc, width=70, initial_indent="", subsequent_indent="    ")
        return Text.assemble((name, "bright_blue"), (": ", "bright_blue"), (wrapped, "default"))

    for command in all_commands():
        doc = command.__doc__ if command.__doc__ else ""
        rprint(format_doc(command.__name__, doc))
        rprint()

    rprint(Text("\nAvailable kmd actions:\n", style="bright_green"))
    actions = load_all_actions()
    for action in actions.values():
        rprint(format_doc(action.name, action.description))
        rprint()


@register_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace.
    """
    if workspace_name:
        ws_name, ws_dir = canon_workspace_name(workspace_name)
        if not re.match(r"^\w+$", ws_name):
            raise ValueError(
                "Use an alphanumeric name (no spaces or special characters) for the workspace"
            )
        os.makedirs(ws_dir, exist_ok=True)
        os.chdir(ws_dir)
        command_output("Changed to workspace: %s", ws_name)
    show_workspace_info()


@register_command
def select(*paths: str) -> None:
    """
    Get or show the current selection.
    """
    if paths:
        store_paths = [StorePath(path) for path in paths]
        current_workspace().set_selection(store_paths)
        selection = store_paths
    else:
        selection = current_workspace().get_selection()
    if not selection:
        command_output("No selection.")
    else:
        command_output(
            "Selected %s %s:\n%s",
            len(selection),
            plural("item", len(selection)),
            format_lines(selection),
        )


@register_command
def unselect(*paths: str) -> None:
    """
    Remove items from the current selection. Handy if you've selected some items and
    wish to unselect a few of them.
    """
    if not paths:
        raise ValueError("No paths provided to unselect")
    previous_selection = current_workspace().get_selection()
    new_selection = current_workspace().unselect([StorePath(path) for path in paths])
    command_output(
        "Unselected %s %s, %s now selected:\n%s",
        len(previous_selection) - len(new_selection),
        plural("item", len(previous_selection) - len(new_selection)),
        len(new_selection),
        format_lines(new_selection),
    )


@register_command
def show(path: Optional[str] = None) -> None:
    """
    Show the contents of a file.
    """

    if path:
        open_platform_specific(path)
    else:
        selection = current_workspace().get_selection()
        if not selection:
            raise ValueError("No selection")
        open_platform_specific(selection[0])


@register_command
def add_resource(*files_or_urls: str) -> None:
    """
    Add a file or URL resource to the workspace.
    """
    if not files_or_urls:
        raise ValueError("No files or URLs provided to import")
    store_paths = [current_workspace().add_resource(r) for r in files_or_urls]
    command_output(
        "Imported %s %s:\n%s",
        len(store_paths),
        plural("item", len(store_paths)),
        format_lines(store_paths),
    )
    select(*store_paths)


@register_command
def archive(path: StorePath) -> None:
    """
    Archive the item at the given path.
    """
    current_workspace().archive(path)
    command_output("Archived %s", path)


@register_command
def unarchive(path: StorePath) -> None:
    """
    Unarchive the item at the given path.
    """
    store_path = current_workspace().unarchive(path)
    command_output("Unarchived %s", store_path)


@register_command
def files(path: Optional[str] = None, full: Optional[bool] = True) -> None:
    """
    List all files in a directory or workspace.
    """
    base_dir = path or str(current_workspace().base_dir)
    folder_tally = {}

    print(f"Listing files in {base_dir}")
    for dirname, dirnames, filenames in os.walk(base_dir):
        # TODO: Better sort options.
        dirnames.sort()
        filenames.sort()

        folder_tally[dirname] = len(filenames)
        tally = f" - {len(filenames)} files" if len(filenames) > 0 else ""
        dirname_rel = os.path.relpath(dirname, base_dir)

        if dirname_rel.startswith("."):
            continue

        command_output(f"{dirname_rel}{tally}", color="bright_blue")
        if full:
            for file in filenames:
                if file.startswith("."):
                    continue

                full_path = os.path.join(dirname, file)
                file_size = humanize.naturalsize(os.path.getsize(full_path))
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
                file_mod_time = file_mod_time.split(".", 1)[0]
                file_rel = os.path.relpath(file, base_dir)
                if file_rel.startswith("."):
                    continue

                # TODO: Show actual lines and words of body text as well as size with wc. Indicate if body is empty.
                command_output("  %-10s %s  %s" % (file_size, file_mod_time, file_rel))

    total_items = sum(folder_tally.values())
    command_output(
        f"\n{total_items} items total in {len(folder_tally)} folders", color="bright_blue"
    )
