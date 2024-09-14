import os
import sys
from datetime import datetime
from os.path import basename, getmtime, getsize
from pathlib import Path
from typing import cast, List, Optional, Sequence

from humanize import naturalsize, naturaltime
from rich import get_console
from rich.text import Text
from strif import copyfile_atomic

from kmd.action_defs import load_all_actions
from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger, log_file_path, log_objects_dir, reset_logging
from kmd.config.settings import global_settings, LogLevel, update_global_settings
from kmd.config.text_styles import (
    COLOR_EMPH,
    COLOR_HEADING,
    COLOR_HINT,
    COLOR_LOGO,
    COLOR_STATUS,
    EMOJI_TRUE,
    EMOJI_WARN,
    HRULE,
    LOGO,
    PROMPT_ASSIST,
    SPINNER,
)
from kmd.errors import InvalidInput, InvalidState
from kmd.file_formats.frontmatter_format import fmf_read, fmf_read_raw, fmf_strip_frontmatter
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.file_storage.file_listings import walk_by_folder
from kmd.file_storage.file_store import initialize_store_dirs
from kmd.file_storage.workspaces import (
    check_strict_workspace_name,
    current_workspace,
    current_workspace_info,
    is_workspace_dir,
    resolve_workspace_name,
)
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assistance
from kmd.help.help_page import output_help_page
from kmd.lang_tools.inflection import plural
from kmd.model import is_ignored, ItemType, StorePath, USER_SETTABLE_PARAMS
from kmd.model.file_formats_model import file_mime_type, guess_format, join_filename, split_filename
from kmd.model.output_model import CommandOutput
from kmd.preconditions import ALL_PRECONDITIONS
from kmd.preconditions.precondition_checks import actions_matching_paths
from kmd.shell_tools.native_tools import (
    CmdlineTool,
    edit_files,
    tail_file,
    terminal_show_image,
    tool_check,
    view_file_native,
)
from kmd.text_chunks.parse_divs import parse_divs
from kmd.text_formatting.doc_formatting import normalize_text_file
from kmd.text_formatting.text_formatting import fmt_lines, fmt_path
from kmd.text_ui.command_output import (
    format_name_and_description,
    output,
    output_assistance,
    output_heading,
    output_response,
    output_status,
    Wrap,
)
from kmd.util.obj_utils import remove_values
from kmd.util.parse_utils import format_key_value, parse_key_value
from kmd.util.type_utils import not_none
from kmd.util.url import is_url, Url
from kmd.version import get_version
from kmd.viz.graph_view import assemble_workspace_graph, open_graph_view
from kmd.web_content.web_fetch import fetch_and_cache

log = get_logger(__name__)


@kmd_command
def welcome() -> None:
    """
    Print a welcome message.
    """

    from kmd.docs.topics.welcome import __doc__ as welcome_doc

    output()
    output(HRULE, color=COLOR_HINT)
    version = "v%s" % get_version()
    padding = " " * (len(HRULE) - len(LOGO) - len(version))
    output(Text(LOGO, style=COLOR_LOGO) + Text(padding + version, style=COLOR_HINT))
    output(HRULE, color=COLOR_HINT)
    output()
    output("Welcome to kmd.\n", color=COLOR_HEADING)
    output()
    output(not_none(welcome_doc), text_wrap=Wrap.WRAP_FULL)
    output(HRULE, color=COLOR_HINT)


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
    tail_file(log_file_path())


@kmd_command
def clear_logs() -> None:
    """
    Clear the logs for the current workspace. Logs for the current workspace will be lost
    permanently!
    """
    log_path = log_file_path()
    if log_path.exists():
        with open(log_path, "w"):
            pass
    obj_dir = log_objects_dir()
    if obj_dir.exists():
        trash(obj_dir)
        os.makedirs(obj_dir, exist_ok=True)

    output_status("Logs cleared:\n%s", fmt_lines([fmt_path(log_path)]))


@kmd_command
def cache_list(media: bool = False, web: bool = False) -> None:
    """
    List the contents of the media and/or web caches. By default lists both media and web caches.
    """
    if not media and not web:
        media = True
        web = True

    if media:
        files(global_settings().media_cache_dir)
        output()
    if web:
        files(global_settings().web_cache_dir)
        output()


@kmd_command
def cache_local(*path_or_urls: str) -> None:
    """
    Cache the given file in the web cache. Downloads any URL or copies a local file.
    """
    output()
    for path_or_url in path_or_urls:
        locator = cast(Url, path_or_url) if is_url(path_or_url) else Path(path_or_url)
        cache_path, was_cached = fetch_and_cache(locator)
        cache_str = " (already cached)" if was_cached else ""
        output(f"{fmt_path(path_or_url)}{cache_str}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
        output(f"{cache_path}", text_wrap=Wrap.INDENT_ONLY)
        output()


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
def init(path: Optional[str] = None) -> None:
    """
    Initialize a new workspace at the given path.
    """
    dir = Path(path) if path else Path(".")
    if is_workspace_dir(dir):
        raise InvalidInput("Workspace already exists: %s", dir)
    if not dir.exists():
        dir.mkdir()
    initialize_store_dirs(dir)

    current_workspace(log_on_change=False).log_store_info()


@kmd_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace (if no arg given), or switch to a new workspace,
    creating it if it doesn't exist. Equivalent to `mkdir some_name.kb`.
    """
    if workspace_name:
        ws_name, ws_path = resolve_workspace_name(workspace_name)

        if not ws_path.exists():
            # Enforce reasonable naming on new workspaces.
            check_strict_workspace_name(ws_name)

        os.makedirs(ws_path, exist_ok=True)
        os.chdir(ws_path)
        output_status(f"Changed to workspace: {ws_name} ({ws_path})")

    current_workspace(log_on_change=False).log_store_info()


@kmd_command
def reload_workspace() -> None:
    """
    Reload the current workspace. Helpful for debugging to reset in-memory state.
    """
    current_workspace().reload()


@kmd_command
def select(*paths: str, stdin: bool = False) -> CommandOutput:
    """
    Get or show the current selection.
    """
    ws = current_workspace()

    # TODO: It would be nice to be able to read stdin from a pipe but this isn't working rn.
    # Globally we have THREAD_SUBPROCS=False to avoid hard-to-interrupt subprocesses.
    # But xonsh seems to hang with stdin unless we modify the spec to be threadable?
    # https://xon.sh/tutorial.html#callable-aliases
    # https://github.com/xonsh/xonsh/blob/main/xonsh/aliases.py#L1070
    if stdin:
        paths = tuple(sys.stdin.read().splitlines())

    if paths:
        store_paths = [StorePath(path) for path in paths]
        ws.set_selection(store_paths)
        selection = store_paths
    else:
        selection = ws.get_selection()

    return CommandOutput(selection=selection, show_selection=True)


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
            fmt_lines(new_selection),
        )


def _resolve_path_arg(path_str: str) -> Path | StorePath:
    path = Path(path_str)
    if path.is_absolute() or path.exists():
        return path
    else:
        return StorePath(path_str)


def _assemble_paths(*paths: Optional[str]) -> List[StorePath | Path]:
    """
    Assemble store paths from the current workspace, or the current selection if
    no paths are given.
    """

    out_paths = [_resolve_path_arg(path) for path in paths if path]
    if not out_paths:
        ws = current_workspace()
        out_paths = ws.get_selection()
        if not out_paths:
            raise InvalidInput("No selection")
    return cast(List[StorePath | Path], out_paths)


# TODO: Get more commands to work on files outside the workspace by importing them first.
def _check_store_paths(paths: Sequence[StorePath | Path]) -> List[StorePath]:
    """
    Check that all paths are store paths.
    """
    ws = current_workspace()
    for path in paths:
        if not ws.exists(StorePath(path)):
            raise InvalidInput(f"Store path not found: {path}")
    return [StorePath(str(path)) for path in paths]


@kmd_command
def show(path: Optional[str] = None, pager: bool = False) -> None:
    """
    Show the contents of a file if one is given, or the first file if multiple files
    are selected.
    """
    try:
        input_paths = _assemble_paths(path)
        input_path = input_paths[0]

        if isinstance(input_path, StorePath):
            # Optionally, if we can inline display the image (like in kitty) above the text representation, do that.
            ws = current_workspace()

            item = ws.load(input_path)
            if item.thumbnail_url:
                try:
                    local_path, _was_cached = fetch_and_cache(item.thumbnail_url)
                    terminal_show_image(local_path)
                except Exception as e:
                    log.info("Had trouble showing thumbnail image (will skip): %s", e)
                    output(f"[Image: {item.thumbnail_url}]", color=COLOR_HINT)

            view_file_native(ws.base_dir / input_path, use_pager=pager)
        else:
            view_file_native(input_path, use_pager=pager)
    except (InvalidInput, InvalidState):
        if path:
            # If path is absolute or we couldbn't get a selection, just show the file.
            view_file_native(path, use_pager=pager)
        else:
            raise InvalidInput("No selection")


@kmd_command
def cbcopy(path: Optional[str] = None, raw: bool = False) -> None:
    """
    Copy the contents of a file (or the first file in the selection) to the OS-native
    clipboard. If `raw` is true, copy the full exact contents of the file. Otherwise,
    omits any frontmatter if present.
    """
    import pyperclip

    input_paths = _assemble_paths(path)
    input_path = input_paths[0]

    format = guess_format(input_path)
    if not format or not format.is_text():
        raise InvalidInput(f"Cannot copy non-text files to clipboard: {fmt_path(input_path)}")

    if raw:
        with open(input_path, "r") as f:
            content = f.read()

        pyperclip.copy(content)
        output_status(
            "Copied raw contents of file to clipboard (%s chars):\n%s",
            len(content),
            fmt_lines([fmt_path(input_path)]),
        )
    else:
        content, metadata_str = fmf_read_raw(input_path)
        pyperclip.copy(content)
        skip_msg = ""
        if metadata_str:
            skip_msg = f", skipping {len(metadata_str)} chars of frontmatter"
        output_status(
            "Copied contents of file to clipboard (%s chars%s):\n%s",
            len(content),
            skip_msg,
            fmt_lines([fmt_path(input_path)]),
        )


@kmd_command
def edit(path: Optional[str] = None, all: bool = False) -> None:
    """
    Edit the contents of a file using the user's default editor (or defaulting to nano).
    If multiple files are selected, edit the first one.
    """
    input_paths = _assemble_paths(path)
    if not all:
        input_paths = [input_paths[0]]

    edit_files(*input_paths)


@kmd_command
def save(path: Optional[str] = None) -> None:
    """
    Save the current selection to the given directory (which must exist), or to the
    current directory if no target given. Output will have YAML frontmatter.
    """
    ws = current_workspace()
    store_paths = ws.get_selection()
    target_dir = Path(path) if path else Path(".")

    if not target_dir.exists():
        raise InvalidInput(f"Target directory does not exist: {target_dir}")

    for store_path in store_paths:
        target_path = target_dir / basename(store_path)
        log.message("Saving: %s -> %s", store_path, target_path)
        copyfile_atomic(ws.base_dir / store_path, target_path)


@kmd_command
def strip_frontmatter(*paths: str) -> None:
    """
    Strip the frontmatter from the given files.
    """
    if not paths:
        raise InvalidInput("Provide one or more paths")
    for path in paths:
        log.message("Stripping frontmatter from: %s", path)
        fmf_strip_frontmatter(path)


@kmd_command
def size_summary(*paths: str, slow: bool = False) -> None:
    """
    Show a summary of the size and HTML structure of the items at the given paths.
    """
    input_paths = _assemble_paths(*paths)
    output()
    for input_path in input_paths:
        output(f"{fmt_path(input_path)}:", color=COLOR_EMPH)
        body, _frontmatter = fmf_read(input_path)
        if body:
            parsed_body = parse_divs(body)
            output(parsed_body.size_summary(fast=not slow), text_wrap=Wrap.INDENT_ONLY)
        else:
            output("No text body", text_wrap=Wrap.INDENT_ONLY)
        output()


@kmd_command
def file_info(*paths: str) -> None:
    """
    Show information about the file at the given path.
    """
    input_paths = _assemble_paths(*paths)
    output()
    for input_path in input_paths:
        mime_type = file_mime_type(input_path)
        output(f"{fmt_path(input_path)}:", color=COLOR_EMPH)
        output(f"{mime_type}", text_wrap=Wrap.INDENT_ONLY)
        output()


@kmd_command
def param(*args: str) -> None:
    """
    Show or set currently set of global parameters, which are settings that may be used by
    commands and actions or to override default parameters.
    """
    ws = current_workspace()
    if args:
        new_key_vals = dict([parse_key_value(arg) for arg in args])

        for key in new_key_vals:
            if key not in USER_SETTABLE_PARAMS:
                raise InvalidInput(f"Unknown parameter: {key}")

        for key, value in new_key_vals.items():
            param = USER_SETTABLE_PARAMS[key]
            if value and param.valid_values and value not in param.valid_values:
                raise InvalidInput(f"Unrecognized value for parameter `{key}`: {value}")

        current_params = ws.get_params()
        new_params = {**current_params, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        ws.set_param(new_params)

    output_heading("Available Parameters")

    for ap in USER_SETTABLE_PARAMS.values():
        output(format_name_and_description(ap.name, ap.full_description()))
        output()

    params = ws.get_params()
    if not params:
        output_status("No parameters are set.")
    else:
        output_heading("Current Parameters")
        for key, value in params.items():
            output(format_key_value(key, value))
        output()


@kmd_command
def settings() -> None:
    """
    Show the current settings.
    """
    settings = global_settings()
    output_heading("Settings")

    for name, value in settings.__dict__.items():
        output(format_name_and_description(name, str(value)))

    output()


@kmd_command
def log_level(level_str: Optional[str] = None, console: bool = False) -> None:
    """
    Set the log level. Sets console log level if `console` is true, otherwise sets file log level.
    """
    if level_str:
        level = LogLevel.parse(level_str)
        with update_global_settings() as settings:
            if console:
                settings.console_log_level = level
            else:
                settings.log_level = level

        reset_logging()

    output()
    output(format_name_and_description("log_level", global_settings().log_level.name))
    output(
        format_name_and_description("console_log_level", global_settings().console_log_level.name)
    )
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
        fmt_lines(store_paths),
    )
    select(*store_paths)


@kmd_command
def archive(*paths: str) -> None:
    """
    Archive the items at the given path, or the current selection.
    """
    store_paths = _check_store_paths(_assemble_paths(*paths))
    ws = current_workspace()
    for store_path in store_paths:
        ws.archive(store_path)

    output_status(f"Archived:\n{fmt_lines(store_paths)}")

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
def clear_archive() -> None:
    """
    Empty the archive to trash.
    """
    ws = current_workspace()
    trash(ws.archive_dir)
    os.makedirs(ws.archive_dir, exist_ok=True)


@kmd_command
def trash(*paths: str) -> None:
    """
    Trash the items at the given paths. Uses OS-native trash or recycle bin on Mac, Windows, or Linux.
    """
    from send2trash import send2trash

    send2trash(list(paths))
    output_status(f"Deleted (check trash or recycling bin to recover):\n{fmt_lines(paths)}")


@kmd_command
def suggest_actions(all: bool = False) -> None:
    """
    Suggest actions that can be applied to the current selection.
    """
    applicable_actions(brief=True, all=all)


@kmd_command
def applicable_actions(*paths: str, brief: bool = False, all: bool = False) -> None:
    """
    Show the actions that are applicable to the current selection.
    This is a great command to use at any point to see what actions are available!
    """
    store_paths = _check_store_paths(_assemble_paths(*paths))
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
        output(
            ", ".join(f"`{name}`" for name in action_names), extra_indent="    ", color=COLOR_STATUS
        )
        output()
    else:
        output_status("Applicable actions for items:\n %s", fmt_lines(store_paths))

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

    output_status("Precondition check for selection:\n %s", fmt_lines(selection))

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
    store_paths = _check_store_paths(_assemble_paths(*paths))
    ws = current_workspace()

    ws.vector_index.index_items([ws.load(store_path) for store_path in store_paths])

    output_status(f"Indexed:\n{fmt_lines(store_paths)}")


@kmd_command
def unindex(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    store_paths = _check_store_paths(_assemble_paths(*paths))
    ws = current_workspace()
    ws.vector_index.unindex_items([ws.load(store_path) for store_path in store_paths])

    output_status(f"Unindexed:\n{fmt_lines(store_paths)}")


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
def files(
    *paths: str,
    all: bool = False,
    summary: Optional[bool] = False,
    iso_time: Optional[bool] = False,
) -> None:
    """
    List files or folders in the current directory. Shows the full current workspace if
    no path is provided.
    """
    if len(paths) == 0:
        paths_to_show = (Path("."),)
    else:
        paths_to_show = [Path(path) for path in paths]

    base_dir, is_sandbox = current_workspace_info()
    relative_to = base_dir if base_dir and not is_sandbox else Path(".")

    total_folders, total_files = 0, 0

    output()

    for path in paths_to_show:
        # If we're explicitly looking in a hidden directory, show hidden files.
        show_hidden = all or (path is not None and is_ignored(path))

        for dirname, filenames in walk_by_folder(path, relative_to, show_hidden):
            # Show tally for this directory.
            nfiles = len(filenames)
            if nfiles > 0:
                output(f"\n{fmt_path(dirname)} - {nfiles} files", color=COLOR_EMPH)

            for filename in filenames:
                full_path = os.path.join(dirname, filename)

                # Now show all the files in that directory.
                if not summary:
                    file_size = naturalsize(getsize(full_path)).replace("Bytes", "B")

                    if not iso_time:
                        file_mod_time = (
                            naturaltime(datetime.fromtimestamp(getmtime(full_path)))
                            .replace("second", "sec")
                            .replace("minute", "min")
                        )
                    else:
                        file_mod_time = (
                            datetime.fromtimestamp(getmtime(full_path)).isoformat().split(".", 1)[0]
                        )

                    parent_dir = basename(dirname)
                    display_name = f"{parent_dir}/{filename}" if parent_dir != "." else filename
                    display_name = fmt_path(display_name)

                    # TODO: Option to show size summary. Indicate if body is empty.
                    output(
                        "  %8s  %12s  %s",
                        file_size,
                        file_mod_time,
                        display_name,
                        text_wrap=Wrap.NONE,
                    )

            output()

            total_folders += 1
            total_files += nfiles

        output(f"\n{total_files} items total in {total_files} folders", color=COLOR_EMPH)


@kmd_command
def search(
    query_str: str, *paths: str, sort: str = "path", ignore_case: bool = False
) -> CommandOutput:
    """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex.
    """
    tool_check().require(CmdlineTool.ripgrep)
    from ripgrepy import RipGrepNotFound, Ripgrepy

    strip_prefix = None
    if not paths:
        paths = (".",)
        strip_prefix = "./"
    try:
        rg = Ripgrepy(query_str, *paths)
        rg = rg.files_with_matches().sort(sort)
        if ignore_case:
            rg = rg.ignore_case()
        rg_output = rg.run().as_string
        results: List[str] = [
            line.lstrip(strip_prefix) if strip_prefix and line.startswith(strip_prefix) else line
            for line in rg_output.splitlines()
        ]

        return CommandOutput(results, show_result=True)
    except RipGrepNotFound:
        raise InvalidState("`rg` command not found. Install ripgrep to use the search command.")


@kmd_command
def graph_view(
    docs_only: bool = False, concepts_only: bool = False, resources_only: bool = False
) -> None:
    """
    Open a graph view of the current workspace.
    """
    if docs_only:
        item_filter = lambda item: item.type == ItemType.doc
    elif concepts_only:
        item_filter = lambda item: item.type == ItemType.concept
    elif resources_only:
        item_filter = lambda item: item.type == ItemType.resource
    else:
        item_filter = None
    open_graph_view(assemble_workspace_graph(item_filter))


@kmd_command
def normalize(*paths: str) -> None:
    """
    Normalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    # TODO: Make a version of this that works outside the workspace on Markdown files,
    # (or another verion just called `format` that does this).
    ws = current_workspace()
    store_paths = _check_store_paths(_assemble_paths(*paths))

    canon_paths = []
    for store_path in store_paths:
        log.message("Canonicalizing: %s", fmt_path(store_path))
        for item_store_path in ws.walk_items(store_path):
            try:
                ws.normalize(item_store_path)
            except InvalidInput as e:
                log.warning(
                    "%s Could not canonicalize %s: %s", EMOJI_WARN, fmt_path(item_store_path), e
                )
            canon_paths.append(item_store_path)

    if len(canon_paths) == 1:
        select(*canon_paths)

    # TODO: Also consider implementing duplicate elimination here.


@kmd_command
def reformat(*paths: str, inplace: bool = False) -> None:
    """
    Format text, Markdown, or HTML according to kmd conventions.
    Saves files
    """
    for path in paths:
        target_path = None
        if not inplace:
            dirname, name, item_type, ext = split_filename(path)
            new_name = f"{name}_formatted"
            target_path = join_filename(dirname, new_name, item_type, ext)

        normalize_text_file(path, target_path=target_path, inplace=inplace)

        if target_path:
            log.message("Formatted: %s -> %s", fmt_path(path), fmt_path(target_path))
        else:
            log.message("Formatted in place: %s", fmt_path(path))


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
