import os
from os.path import getmtime, basename, getsize, join
import re
import textwrap
from typing import Callable, List, Optional
from datetime import datetime
from humanize import naturaltime, naturalsize
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
    workspace = current_workspace()
    if len(paths) == 0:
        paths = (str(workspace.base_dir),)

    total_folders, total_files = 0, 0

    for path in paths:
        # If we're explicitly looking in a hidden directory, show hidden files.
        show_hidden = skippable_file(path)

        for store_dirname, filenames in workspace.walk_by_folder(StorePath(path), show_hidden):
            # Show tally for this directory.
            nfiles = len(filenames)
            if nfiles > 0:
                command_output(f"{store_dirname} - {nfiles} files", color="bright_blue")

            for filename in filenames:
                full_path = join(workspace.base_dir, store_dirname, filename)

                # Now show all the files in that directory.
                if full:
                    file_size = naturalsize(getsize(full_path))

                    if human_time:
                        file_mod_time = naturaltime(datetime.fromtimestamp(getmtime(full_path)))
                    else:
                        file_mod_time = (
                            datetime.fromtimestamp(getmtime(full_path)).isoformat().split(".", 1)[0]
                        )

                    parent_dir = basename(store_dirname)
                    display_name = f"{parent_dir}/{filename}" if parent_dir != "." else filename

                    # TODO: Show actual lines and words of body text as well as size with wc. Indicate if body is empty.
                    command_output("  %-10s %-14s  %s" % (file_size, file_mod_time, display_name))

            total_folders += 1
            total_files += nfiles

        command_output(f"\n{total_files} items total in {total_files} folders", color="bright_blue")


@register_command
def canonicalize(*paths: str) -> None:
    """
    Canonicalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    workspace = current_workspace()

    if len(paths) == 0:
        paths = (str(workspace.base_dir),)

    canon_paths = []
    for path in paths:
        log.message("Canonicalizing files in path: %s", path)
        for store_path in workspace.walk_items(StorePath(path)):
            try:
                workspace.canonicalize(store_path)
            except ValueError as e:
                log.warning("Could not canonicalize %s: %s", store_path, e)
            canon_paths.append(store_path)

    if len(canon_paths) == 1:
        select(*canon_paths)

    # TODO: Also consider implementing duplicate elimination here.
