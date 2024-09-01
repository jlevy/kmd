import os
from os.path import getmtime, basename, getsize, join
import re
import subprocess
from typing import List, Optional, cast
from datetime import datetime
from humanize import naturaltime, naturalsize
from rich import get_console
from kmd.action_defs import load_all_actions
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assistance
from kmd.help.help_page import output_help_page
from kmd.commands.command_registry import kmd_command
from kmd.file_storage.yaml_util import to_yaml_string
from kmd.media.web import fetch_and_cache
from kmd.preconditions import ALL_PRECONDITIONS
from kmd.preconditions.precondition_checks import actions_matching_paths
from kmd.text_chunks.parse_divs import parse_divs
from kmd.text_ui.command_output import (
    Wrap,
    format_name_and_description,
    output,
    output_assistance,
    output_heading,
    output_response,
    output_status,
)
from kmd.shell_tools.native_tools import (
    edit_files,
    show_file_platform_specific,
    terminal_show_image_graceful,
)
from kmd.config.text_styles import (
    COLOR_EMPH,
    COLOR_HEADING,
    COLOR_LOGO,
    EMOJI_TRUE,
    EMOJI_WARN,
    LOGO,
    PROMPT_ASSIST,
    SPINNER,
)
from kmd.file_storage.file_store import skippable_file
from kmd.file_storage.workspaces import canon_workspace_name, current_workspace
from kmd.model.params_model import USER_SETTABLE_PARAMS
from kmd.model.errors_model import InvalidInput, InvalidState
from kmd.model.locators import StorePath
from kmd.text_formatting.text_formatting import format_lines
from kmd.lang_tools.inflection import plural
from kmd.config.logger import get_logger, log_file
from kmd.util.obj_utils import remove_values
from kmd.util.parse_utils import format_key_value, parse_key_value
from kmd.util.type_utils import not_none
from kmd.version import get_version
from kmd.viz.graph_view import assemble_workspace_graph, open_graph_view

log = get_logger(__name__)


@kmd_command
def welcome() -> None:
    """
    Print a welcome message.
    """

    from kmd.docs.topics.welcome import __doc__ as welcome_doc

    output()
    output(LOGO, color=COLOR_LOGO)
    output()
    output("Welcome to kmd.\n", color=COLOR_HEADING)
    output()
    output(not_none(welcome_doc), text_wrap=Wrap.WRAP_FULL)


@kmd_command
def kmd_help() -> None:
    """
    kmd help. Lists all available actions.
    """
    # TODO: Take an argument to show help for a specific command or action.

    output_help_page()


@kmd_command
def logs() -> None:
    """
    Page through the logs for the current workspace.
    """
    subprocess.run(["less", "+G", log_file()])


@kmd_command
def assist(input: Optional[str] = None) -> None:
    """
    Invoke the kmd assistant. You don't normally need this command as it is the same as just
    asking a question (a question ending with ?) on the kmd console.
    """
    if not input:
        input = prompt_simple_string(
            "What do you need help with? (Ask any question or press enter to see main `kmd_help` page.)",
            prompt_symbol=PROMPT_ASSIST,
        )
        if not input.strip():
            kmd_help()
            return
    with get_console().status("Thinking…", spinner=SPINNER):
        output_assistance(assistance(input))


@kmd_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace (if no arg given), or switch to a new workspace,
    creating it if it doesn't exist. Equivalent to `mkdir some_name.kb`.
    """
    if workspace_name:
        ws_name, ws_dir = canon_workspace_name(workspace_name)
        if not re.match(r"^[\w-]+$", ws_name):
            raise InvalidInput(
                "Use an alphanumeric name (no spaces or special characters) for the workspace"
            )
        os.makedirs(ws_dir, exist_ok=True)
        os.chdir(ws_dir)
        output_status(f"Changed to workspace: {ws_name}")

    current_workspace().log_store_info()


@kmd_command
def reload_workspace() -> None:
    """
    Reload the current workspace. Helpful for debugging to reset in-memory state.
    """
    current_workspace().reload()

    output()
    current_workspace().log_store_info()
    output()


def print_selection(selection: List[StorePath]) -> None:
    """
    Print the current selection.
    """
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
def select(*paths: str, stdin=None) -> None:
    """
    Get or show the current selection.
    """
    ws = current_workspace()

    # TODO: Get stdin to work for commands like select.
    # Globally we have THREAD_SUBPROCS=False to avoid hard-to-interrupt subprocesses.
    # But xonsh seems to hang with stdin unless we modify the spec to be threadable?
    # https://xon.sh/tutorial.html#callable-aliases
    # https://github.com/xonsh/xonsh/blob/main/xonsh/aliases.py#L1070
    # if stdin:
    #     paths = stdin.read().splitlines()

    if paths:
        store_paths = [StorePath(path) for path in paths]
        ws.set_selection(store_paths)
        selection = store_paths
    else:
        selection = ws.get_selection()

    print_selection(selection)


@kmd_command
def unselect(*paths: str) -> None:
    """
    Remove items from the current selection. Handy if you've selected some items and
    wish to unselect a few of them.
    """
    ws = current_workspace()
    if not paths:
        ws.set_selection([])
        output_status("Cleared selection.")
    else:
        previous_selection = ws.get_selection()
        new_selection = ws.unselect([StorePath(path) for path in paths])

        output_status(
            "Unselected %s %s, %s now selected:\n%s",
            len(previous_selection) - len(new_selection),
            plural("item", len(previous_selection) - len(new_selection)),
            len(new_selection),
            format_lines(new_selection),
        )


def _assemble_paths(*paths: Optional[str]) -> List[StorePath]:
    """
    Assemble store paths from the given paths, or the current selection if
    no paths are given.
    """
    ws = current_workspace()
    store_paths = [StorePath(path) for path in paths if path]
    if not store_paths:
        store_paths = ws.get_selection()
        if not store_paths:
            raise InvalidInput("No selection")
    return store_paths


@kmd_command
def show(path: Optional[str] = None) -> None:
    """
    Show the contents of a file if one is given, or the first file if multiple files are selected.
    """
    store_paths = _assemble_paths(path)
    store_path = store_paths[0]

    # Optionally, if we can inline display the image (like in kitty) above the text representation, do that.
    ws = current_workspace()
    item = ws.load(store_path)
    if item.thumbnail_url:
        try:
            local_path = fetch_and_cache(item.thumbnail_url)
            terminal_show_image_graceful(local_path)
        except Exception as e:
            log.error("Error fetching thumbnail image: %s", e)
    show_file_platform_specific(store_path)


@kmd_command
def edit(path: Optional[str] = None, all: bool = False) -> None:
    """
    Edit the contents of a file using the user's default editor (or defaulting to nano).
    If multiple files are selected, edit the first one.
    """
    store_paths = _assemble_paths(path)
    if not all:
        store_paths = [store_paths[0]]

    edit_files(*store_paths)


@kmd_command
def param(*args: str) -> None:
    """
    Show or set currently set of global parameters, which are settings that may be used by
    commands and actions or to override default action parameters.
    """
    ws = current_workspace()
    if args:
        new_key_vals = dict([parse_key_value(arg) for arg in args])

        for key in new_key_vals:
            if key not in USER_SETTABLE_PARAMS:
                raise InvalidInput(f"Unknown action parameter: {key}")

        for key, value in new_key_vals.items():
            action_param = USER_SETTABLE_PARAMS[key]
            if value and action_param.valid_values and value not in action_param.valid_values:
                raise InvalidInput(f"Unrecognized value for action parameter `{key}`: {value}")

        current_params = ws.get_params()
        new_params = {**current_params, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        ws.set_param(new_params)

    output_heading("Available action parameters")

    for ap in USER_SETTABLE_PARAMS.values():
        output(format_name_and_description(ap.name, ap.full_description()))
        output()

    params = ws.get_params()
    if not params:
        output_status("No action parameters are set.")
    else:
        output_heading("Current action parameters")
        for key, value in params.items():
            output(format_key_value(key, value))
        output()


@kmd_command
def add_resource(*files_or_urls: str) -> None:
    """
    Add a file or URL resource to the workspace.
    """
    if not files_or_urls:
        raise InvalidInput("No files or URLs provided to import")

    ws = current_workspace()
    store_paths = [ws.add_resource(r) for r in files_or_urls]
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
    store_paths = _assemble_paths(*paths)
    ws = current_workspace()
    for store_path in store_paths:
        ws.archive(store_path)

    output_status(f"Archived:\n{format_lines(store_paths)}")

    select()


@kmd_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    ws = current_workspace()
    for path in paths:
        store_path = ws.unarchive(StorePath(path))
        output_status(f"Unarchived: {store_path}")


@kmd_command
def size_summary(*paths: str) -> None:
    """
    Show a summary of the size and HTML structure of the items at the given paths.
    """
    store_paths = _assemble_paths(*paths)
    ws = current_workspace()
    output()
    for store_path in store_paths:
        item = ws.load(store_path)
        output(f"{store_path}:", color=COLOR_EMPH)

        if item.body:
            parsed_body = parse_divs(item.body)
            output(f"{parsed_body.size_summary()}", text_wrap=Wrap.INDENT_ONLY)
        else:
            output("No text body", text_wrap=Wrap.INDENT_ONLY)
        output()


@kmd_command
def suggest_actions() -> None:
    """
    Suggest actions that can be applied to the current selection.
    """
    applicable_actions(brief=True)


@kmd_command
def applicable_actions(*paths: str, brief: bool = False, all: bool = False) -> None:
    """
    Show the actions that are applicable to the current selection.
    This is a great command to use at any point to see what actions are available!
    """
    store_paths = _assemble_paths(*paths)
    ws = current_workspace()

    actions = load_all_actions(base_only=False).values()
    applicable_actions = list(
        actions_matching_paths(
            actions,
            ws,
            store_paths,
            include_no_precondition=all,
        )
    )

    if not applicable_actions:
        output_status("No applicable actions for selection.")
        return

    if brief:
        action_names = [action.name for action in applicable_actions]
        output_status("Applicable actions:")
        output(", ".join(f"`{name}`" for name in action_names))
        output()
    else:
        output_status("Applicable actions for items:\n %s", format_lines(store_paths))

        for action in applicable_actions:
            precondition_str = (
                f"(matches precondition {action.precondition })"
                if action.precondition
                else "(no precondition)"
            )
            output(
                format_name_and_description(
                    action.name, action.description, extra_note=precondition_str
                )
            )
            output()


@kmd_command
def preconditions() -> None:
    """
    List all preconditions and if the current selection meets them.
    """

    ws = current_workspace()
    selection = ws.get_selection()
    if not selection:
        raise InvalidInput("No selection")

    items = [ws.load(item) for item in selection]

    output_status("Precondition check for selection:\n %s", format_lines(selection))

    for precondition in ALL_PRECONDITIONS:
        satisfied = all(precondition(item) for item in items)
        emoji = EMOJI_TRUE if satisfied else " "
        satisfied_str = "satisfied" if satisfied else "not satisfied"
        output(f"{emoji} {precondition} {satisfied_str}", text_wrap=Wrap.NONE)

    output()


@kmd_command
def index(*paths: str) -> None:
    """
    Index the items at the given path, or the current selection.
    """
    store_paths = _assemble_paths(*paths)
    ws = current_workspace()

    ws.vector_index.index_items([ws.load(store_path) for store_path in store_paths])

    output_status(f"Indexed:\n{format_lines(store_paths)}")


@kmd_command
def unindex(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    store_paths = _assemble_paths(*paths)
    ws = current_workspace()
    ws.vector_index.unindex_items([ws.load(store_path) for store_path in store_paths])

    output_status(f"Unindexed:\n{format_lines(store_paths)}")


def _output_scored_node(scored_node, show_metadata: bool = True):
    from llama_index.core.schema import TextNode

    node = cast(TextNode, scored_node.node)
    output()
    output(
        f"Score {scored_node.score}\n    {node.ref_doc_id}\n    node {node.node_id}",
        text_wrap=Wrap.NONE,
    )
    output_response("%s", node.text, text_wrap=Wrap.WRAP_INDENT)

    if show_metadata and node.metadata:
        output("%s", to_yaml_string(node.metadata), text_wrap=Wrap.INDENT_ONLY)


@kmd_command
def retrieve(query_str: str) -> None:
    """
    Retrieve matches from the index for the given string or query.
    """

    ws = current_workspace()
    results = ws.vector_index.retrieve(query_str)

    output()
    output(f"Matches from {ws.vector_index}:")
    for scored_node in results:
        _output_scored_node(scored_node)


@kmd_command
def query(query_str: str) -> None:
    """
    Query the index for an answer to the given question.
    """
    from llama_index.core.base.response.schema import Response

    ws = current_workspace()
    results = cast(Response, ws.vector_index.query(query_str))

    output()
    output(f"Response from {ws.vector_index}:", text_wrap=Wrap.NONE)
    output_response("%s", results.response, text_wrap=Wrap.WRAP_FULL)

    if results.source_nodes:
        output("Sources:")
        for scored_node in results.source_nodes:
            _output_scored_node(scored_node)

    # if results.metadata:
    #     output("Metadata:")
    #     output("%s", to_yaml_string(results.metadata), text_wrap=Wrap.INDENT_ONLY)


@kmd_command
def files(*paths: str, summary: Optional[bool] = False, iso_time: Optional[bool] = False) -> None:
    """
    List files or folders in a workspace. Shows the full current workspace if no path is provided.
    """
    ws = current_workspace()
    if len(paths) == 0:
        paths_to_show = (None,)
    else:
        paths_to_show = paths

    total_folders, total_files = 0, 0

    output()

    for path in paths_to_show:
        # If we're explicitly looking in a hidden directory, show hidden files.
        show_hidden = path is not None and skippable_file(path)

        for store_dirname, filenames in ws.walk_by_folder(
            StorePath(path) if path else None, show_hidden
        ):
            # Show tally for this directory.
            nfiles = len(filenames)
            if nfiles > 0:
                output(f"\n{store_dirname} - {nfiles} files", color=COLOR_EMPH)

            for filename in filenames:
                full_path = join(ws.base_dir, store_dirname, filename)

                # Now show all the files in that directory.
                if not summary:
                    file_size = naturalsize(getsize(full_path))

                    if not iso_time:
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

            output()

            total_folders += 1
            total_files += nfiles

        output(f"\n{total_files} items total in {total_files} folders", color=COLOR_EMPH)

    output()


@kmd_command
def search(query_str: str, *paths: str, sort: str = "path") -> None:
    """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex.
    """
    from ripgrepy import Ripgrepy, RipGrepNotFound

    strip_prefix = None
    if not paths:
        paths = (".",)
        strip_prefix = "./"
    try:
        rg = Ripgrepy(query_str, *paths)
        results = rg.files_with_matches().sort(sort).run().as_string
        if strip_prefix:
            results = "\n".join(
                line.lstrip(strip_prefix) if line.startswith(strip_prefix) else line
                for line in results.splitlines()
            )
        output("%s", results)
    except RipGrepNotFound:
        raise InvalidState("`rg` command not found. Install ripgrep to use the search command.")


@kmd_command
def graph_view() -> None:
    """
    Open a graph view of the current workspace.
    """
    open_graph_view(assemble_workspace_graph())


@kmd_command
def canonicalize(*paths: str) -> None:
    """
    Canonicalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    ws = current_workspace()
    store_paths = _assemble_paths(*paths)

    canon_paths = []
    for store_path in store_paths:
        log.message("Canonicalizing: %s", store_path)
        for item_store_path in ws.walk_items(store_path):
            try:
                ws.canonicalize(item_store_path)
            except InvalidInput as e:
                log.warning("%s Could not canonicalize %s: %s", EMOJI_WARN, item_store_path, e)
            canon_paths.append(item_store_path)

    if len(canon_paths) == 1:
        select(*canon_paths)

    # TODO: Also consider implementing duplicate elimination here.


@kmd_command
def version() -> None:
    """
    Show the version of kmd.
    """
    output("kmd %s", get_version())


# TODO:
# def define_action_sequence(name: str, *action_names: str):
#     action_registry.define_action_sequence(name, *action_names)
#     log.message("Registered action sequence: %s of actions: %s", name, action_names)
