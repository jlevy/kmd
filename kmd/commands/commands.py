import os
import re
import textwrap
from typing import Callable, List, Optional
from datetime import datetime
import humanize
from rich import print as rprint
from rich.text import Text
from kmd.commands.local_file_tools import open_platform_specific
from kmd.file_storage.file_store import skippable_file

from kmd.file_storage.workspaces import canon_workspace_name, current_workspace, show_workspace_info
from kmd.model.locators import StorePath
from kmd.text_handling.text_formatting import format_lines
from kmd.text_handling.inflection import plural
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
    log.info(
        "Imported %s %s:\n%s",
        len(store_paths),
        plural("item", len(store_paths)),
        format_lines(store_paths),
    )
    select(*store_paths)


@register_command
def archive(*paths: str) -> None:
    """
    Archive the items at the given path, or the current selection.
    """
    if paths:
        store_paths = [StorePath(path) for path in paths]
    else:
        store_paths = current_workspace().get_selection()
        if not store_paths:
            raise ValueError("No selection")
    for store_path in store_paths:
        current_workspace().archive(store_path)
    command_output("Archived:\n%s", format_lines(store_paths))


@register_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    if not paths:
        raise ValueError("No paths provided to unarchive")
    for path in paths:
        store_path = current_workspace().unarchive(StorePath(path))
        command_output("Unarchived %s", store_path)


@register_command
def files(*paths: str, full: Optional[bool] = True, human_time: Optional[bool] = True) -> None:
    """
    List files or folders in a workspace. Shows the full current workspace if no path is provided.
    """
    base_dir = str(current_workspace().base_dir)
    if len(paths) == 0:
        paths = (base_dir,)

    for path in paths:
        if not os.path.exists(path):
            raise ValueError(f"Directory not found: {path}")

    folder_tally = {}

    for path in paths:
        rel_path = os.path.relpath(path, base_dir)
        # FIXME: Need to handle the case where paths are files since os.walk works on directories only.
        for dirname, dirnames, filenames in os.walk(rel_path):
            # TODO: Better sort options.
            dirnames.sort()
            filenames.sort()

            folder_tally[dirname] = len(filenames)
            tally_str = f" - {len(filenames)} files" if len(filenames) > 0 else ""
            rel_dirname = os.path.relpath(dirname, base_dir)

            if skippable_file(rel_dirname):
                continue

            command_output(f"{rel_dirname}{tally_str}", color="bright_blue")
            if full:
                for filename in filenames:
                    rel_filename = os.path.relpath(filename, base_dir)
                    if skippable_file(filename) or skippable_file(rel_filename):
                        continue

                    full_path = os.path.join(dirname, filename)
                    file_size = humanize.naturalsize(os.path.getsize(full_path))

                    if human_time:
                        file_mod_time = humanize.naturaltime(
                            datetime.fromtimestamp(os.path.getmtime(full_path))
                        )
                    else:
                        file_mod_time = (
                            datetime.fromtimestamp(os.path.getmtime(full_path))
                            .isoformat()
                            .split(".", 1)[0]
                        )

                    parent_dir = os.path.basename(dirname)
                    display_name = (
                        f"{parent_dir}/{rel_filename}" if parent_dir != "." else rel_filename
                    )

                    # TODO: Show actual lines and words of body text as well as size with wc. Indicate if body is empty.
                    command_output("  %-10s %-14s  %s" % (file_size, file_mod_time, display_name))

    total_items = sum(folder_tally.values())
    command_output(
        f"\n{total_items} items total in {len(folder_tally)} folders", color="bright_blue"
    )
