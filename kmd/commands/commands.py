import os
from os.path import getmtime, basename, getsize, join
import re
import subprocess
from textwrap import dedent
from typing import Callable, List, Optional
from datetime import datetime
from humanize import naturaltime, naturalsize
from rich import get_console
from kmd.assistant.assistant import assistance
from kmd.text_ui.command_output import (
    Wrap,
    format_action_description,
    output,
    output_assistance,
    output_heading,
    output_status,
)
from kmd.commands.local_file_tools import open_platform_specific
from kmd.text_ui.text_styles import (
    COLOR_EMPH,
    EMOJI_WARN,
)
from kmd.file_storage.file_store import skippable_file
from kmd.file_storage.workspaces import canon_workspace_name, current_workspace, show_workspace_info
from kmd.model.actions_model import ACTION_PARAMS
from kmd.model.errors_model import InvalidInput
from kmd.model.locators import StorePath
from kmd.text_formatting.markdown_normalization import normalize_markdown, wrap_lines
from kmd.text_formatting.text_formatting import format_lines
from kmd.lang_tools.inflection import plural
from kmd.config.logger import LOG_PATH, get_logger
from kmd.util.obj_utils import remove_values
from kmd.util.parse_utils import format_key_value, parse_key_value
from kmd.docs import about_kmd

log = get_logger(__name__)


_commands: List[Callable] = []


def kmd_command(func):
    _commands.append(func)
    return func


def all_commands():
    return sorted(_commands, key=lambda cmd: cmd.__name__)


@kmd_command
def kmd_help() -> None:
    """
    kmd help. Lists all available actions.
    """
    from kmd.action_defs import load_all_actions

    output_heading("About kmd")
    output(
        normalize_markdown(dedent(about_kmd.__doc__).strip(), line_wrapper=wrap_lines),
        text_wrap=Wrap.NONE,
    )

    output_heading("Available commands")
    for command in all_commands():
        doc = command.__doc__ if command.__doc__ else ""
        output(format_action_description(command.__name__, doc))
        output()

    output_heading("Available actions")
    actions = load_all_actions()
    for action in actions.values():
        output(format_action_description(action.name, action.description))
        output()

    output_heading("More help")
    output(
        "Use `kmd_help` for this list. Use `xonfig tutorial` for xonsh help and `help()` for Python help."
    )

    output()


@kmd_command
def assist(input: str) -> None:
    """
    Invoke the kmd assistant. You don't normally need this command as it is the same as just
    asking a question (a question ending with ?) on the kmd console.
    """
    with get_console().status("Thinking…", spinner="dots"):
        output_assistance(assistance(input))


@kmd_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace (if no arg given), or switch to a new workspace,
    creating it if it doesn't exist. Equivalent to `mkdir some_name.kb`.
    """
    if workspace_name:
        ws_name, ws_dir = canon_workspace_name(workspace_name)
        if not re.match(r"^\w+$", ws_name):
            raise InvalidInput(
                "Use an alphanumeric name (no spaces or special characters) for the workspace"
            )
        os.makedirs(ws_dir, exist_ok=True)
        os.chdir(ws_dir)
        output_status(f"Changed to workspace: {ws_name}")
    show_workspace_info()


@kmd_command
def logs() -> None:
    """
    Page through the logs for the current workspace.
    """
    subprocess.run(["less", "+G", LOG_PATH])


@kmd_command
def select(*paths: str) -> None:
    """
    Get or show the current selection.
    """
    workspace = current_workspace()
    if paths:
        store_paths = [StorePath(path) for path in paths]
        workspace.set_selection(store_paths)
        selection = store_paths
    else:
        selection = workspace.get_selection()
    if not selection:
        output_status("No selection.")
    else:
        output_status(
            "Selected %s %s:\n%s",
            len(selection),
            plural("item", len(selection)),
            format_lines(selection),
        )


@kmd_command
def unselect(*paths: str) -> None:
    """
    Remove items from the current selection. Handy if you've selected some items and
    wish to unselect a few of them.
    """
    workspace = current_workspace()
    if not paths:
        workspace.set_selection([])

        output_status("Cleared selection.")
    else:
        previous_selection = workspace.get_selection()
        new_selection = workspace.unselect([StorePath(path) for path in paths])

        output_status(
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
    workspace = current_workspace()
    if path:
        open_platform_specific(path)
    else:
        selection = workspace.get_selection()
        if not selection:
            raise InvalidInput("No selection")
        open_platform_specific(selection[0])


@kmd_command
def param(*args: str) -> None:
    """
    Show or set currently set parameters for actions.
    """
    workspace = current_workspace()
    if args:
        new_key_vals = dict([parse_key_value(arg) for arg in args])

        for key in new_key_vals:
            if key not in ACTION_PARAMS:
                raise InvalidInput(f"Unknown action parameter: {key}")

        for key, value in new_key_vals.items():
            action_param = ACTION_PARAMS[key]
            if value and action_param.valid_values and value not in action_param.valid_values:
                raise InvalidInput(f"Unrecognized value for action parameter {key}: {value}")

        current_params = workspace.get_action_params()
        new_params = {**current_params, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        workspace.set_action_params(new_params)

    output_heading("Available action parameters")

    for ap in ACTION_PARAMS.values():
        output(format_action_description(ap.name, ap.full_description()))
        output()

    params = workspace.get_action_params()
    if not params:
        output_status("No action parameters are set.")
    else:
        output_heading("Current action parameters")
        for key, value in params.items():
            output(format_key_value(key, value))


@kmd_command
def add_resource(*files_or_urls: str) -> None:
    """
    Add a file or URL resource to the workspace.
    """
    workspace = current_workspace()
    if not files_or_urls:
        raise InvalidInput("No files or URLs provided to import")

    store_paths = [workspace.add_resource(r) for r in files_or_urls]
    output_status(
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
    workspace = current_workspace()
    if paths:
        store_paths = [StorePath(path) for path in paths]
    else:
        store_paths = workspace.get_selection()
        if not store_paths:
            raise InvalidInput("No selection")

    for store_path in store_paths:
        workspace.archive(store_path)

    output_status(f"Archived:\n{format_lines(store_paths)}")

    select()


@kmd_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    workspace = current_workspace()
    if paths:
        store_paths = [StorePath(path) for path in paths]
    else:
        store_paths = workspace.get_selection()
        if not store_paths:
            raise InvalidInput("No selection")

    for path in paths:
        store_path = workspace.unarchive(StorePath(path))
        output_status(f"Unarchived: {store_path}")


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
                output(f"\n{store_dirname} - {nfiles} files", color=COLOR_EMPH)

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
                    output(
                        "  %-10s %-14s  %s",
                        file_size,
                        file_mod_time,
                        display_name,
                        text_wrap=Wrap.NONE,
                    )

            total_folders += 1
            total_files += nfiles

        output(f"\n{total_files} items total in {total_files} folders", color=COLOR_EMPH)


@kmd_command
def canonicalize(*paths: str) -> None:
    """
    Canonicalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    workspace = current_workspace()
    if paths:
        store_paths = [StorePath(path) for path in paths]
    else:
        store_paths = workspace.get_selection()
        if not store_paths:
            raise InvalidInput("No selection")

    canon_paths = []
    for store_path in store_paths:
        log.message("Canonicalizing: %s", store_path)
        for item_store_path in workspace.walk_items(store_path):
            try:
                workspace.canonicalize(item_store_path)
            except InvalidInput as e:
                log.warning("%s Could not canonicalize %s: %s", EMOJI_WARN, item_store_path, e)
            canon_paths.append(item_store_path)

    if len(canon_paths) == 1:
        select(*canon_paths)

    # TODO: Also consider implementing duplicate elimination here.


# TODO:
# def define_action_sequence(name: str, *action_names: str):
#     action_registry.define_action_sequence(name, *action_names)
#     log.message("Registered action sequence: %s of actions: %s", name, action_names)
