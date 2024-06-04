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
from kmd.commands.text_styles import COLOR_EMPH, COLOR_HEADING, COLOR_OUTPUT, COLOR_PLAIN
from kmd.config.settings import KMD_WRAP_WIDTH
from kmd.file_storage.file_store import skippable_file
from kmd.file_storage.workspaces import canon_workspace_name, current_workspace, show_workspace_info
from kmd.model.actions_model import ACTION_PARAMS
from kmd.model.locators import StorePath
from kmd.text_handling.text_formatting import format_lines
from kmd.text_handling.inflection import plural
from kmd.config.logger import get_logger
from kmd.util.obj_utils import remove_values
from kmd.util.parse_utils import format_key_value, parse_key_value

log = get_logger(__name__)


_commands: List[Callable] = []


def kmd_command(func):
    _commands.append(func)
    return func


def all_commands():
    return sorted(_commands, key=lambda cmd: cmd.__name__)


def command_output(message: str, *args, color=COLOR_OUTPUT):
    rprint(Text(message % args, color))


def format_docstr(name: str, doc: str) -> Text:
    doc = textwrap.dedent(doc).strip()
    wrapped = textwrap.fill(doc, width=KMD_WRAP_WIDTH, initial_indent="", subsequent_indent="    ")
    return Text.assemble((name, COLOR_EMPH), (": ", COLOR_EMPH), (wrapped, COLOR_PLAIN))


@kmd_command
def kmd_help() -> None:
    """
    kmd help. Lists all available actions.
    """
    from kmd.actions.action_registry import load_all_actions

    rprint(Text("\nAvailable kmd commands:\n", style=COLOR_HEADING))

    for command in all_commands():
        doc = command.__doc__ if command.__doc__ else ""
        rprint(format_docstr(command.__name__, doc))
        rprint()

    rprint(Text("\nAvailable kmd actions:\n", style=COLOR_HEADING))
    actions = load_all_actions()
    for action in actions.values():
        rprint(format_docstr(action.name, action.description))
        rprint()


@kmd_command
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


@kmd_command
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
    rprint()
    if not selection:
        command_output("No selection.")
    else:
        command_output(
            "★ Selected %s %s:\n%s",
            len(selection),
            plural("item", len(selection)),
            format_lines(selection),
        )
    rprint()


@kmd_command
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


@kmd_command
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


@kmd_command
def param(*args: str) -> None:
    """
    Show or set currently set parameters for actions.
    """
    if args:
        new_key_vals = dict([parse_key_value(arg) for arg in args])

        for key in new_key_vals:
            if key not in ACTION_PARAMS:
                raise ValueError(f"Unknown action parameter: {key}")

        for key, value in new_key_vals.items():
            action_param = ACTION_PARAMS[key]
            if value and action_param.valid_values and value not in action_param.valid_values:
                raise ValueError(f"Unrecognized value for action parameter {key}: {value}")

        current_params = current_workspace().get_action_params()
        new_params = {**current_params, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        current_workspace().set_action_params(new_params)

    rprint(Text("\nAvailable action parameters:\n", style=COLOR_HEADING))

    for ap in ACTION_PARAMS.values():
        rprint(format_docstr(ap.name, ap.full_description()))

    rprint()

    params = current_workspace().get_action_params()
    if not params:
        command_output("No action parameters set.")
    else:
        rprint(Text("Action parameters:\n", style=COLOR_HEADING))

        for key, value in params.items():
            command_output(format_key_value(key, value))

    rprint()


@kmd_command
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


@kmd_command
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


@kmd_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    if not paths:
        raise ValueError("No paths provided to unarchive")
    for path in paths:
        store_path = current_workspace().unarchive(StorePath(path))
        command_output("Unarchived %s", store_path)


@kmd_command
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
                command_output(f"\n{store_dirname} - {nfiles} files", color=COLOR_EMPH)

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

        command_output(f"\n{total_files} items total in {total_files} folders", color=COLOR_EMPH)


@kmd_command
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
