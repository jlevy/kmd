import os
import sys
from datetime import datetime
from os.path import basename, getmtime, getsize
from pathlib import Path
from typing import cast, List, Optional, Sequence

from humanize import naturalsize, naturaltime
from rich import get_console
from rich.text import Text

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
from kmd.file_formats.chat_format import tail_chat_history
from kmd.file_formats.frontmatter_format import (
    fmf_read,
    fmf_read_frontmatter_raw,
    fmf_read_raw,
    fmf_strip_frontmatter,
)
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.file_storage.metadata_dirs import MetadataDirs
from kmd.file_storage.workspaces import (
    check_strict_workspace_name,
    current_workspace,
    current_workspace_info,
    resolve_workspace_name,
)
from kmd.file_tools.file_walk import walk_by_folder
from kmd.form_input.prompt_input import prompt_simple_string
from kmd.help.assistant import assist_system_message, assistance
from kmd.help.help_page import output_help_page
from kmd.lang_tools.inflection import plural
from kmd.media import media_tools
from kmd.model.file_formats_model import (
    detect_file_format,
    detect_mime_type,
    Format,
    is_ignored,
    join_filename,
    split_filename,
)
from kmd.model.items_model import Item, ItemType
from kmd.model.output_model import CommandOutput
from kmd.model.params_model import USER_SETTABLE_PARAMS
from kmd.model.paths_model import as_url_or_path, StorePath
from kmd.preconditions import all_preconditions
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
from kmd.text_ui.command_output import (
    format_name_and_description,
    output,
    output_assistance,
    output_heading,
    output_response,
    output_status,
    Wrap,
)
from kmd.util.format_utils import fmt_lines, fmt_path
from kmd.util.obj_utils import remove_values
from kmd.util.parse_key_vals import format_key_value, parse_key_value
from kmd.util.strif import copyfile_atomic
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from kmd.version import get_version
from kmd.viz.graph_view import assemble_workspace_graph, open_graph_view
from kmd.web_content import file_cache_tools

log = get_logger(__name__)


@kmd_command
def welcome() -> None:
    """
    Print a welcome message.
    """
    from kmd.docs import welcome

    output()
    output(HRULE, color=COLOR_HINT)
    version = "v%s" % get_version()
    padding = " " * (len(HRULE) - len(LOGO) - len(version))
    output(Text(LOGO, style=COLOR_LOGO) + Text(padding + version, style=COLOR_HINT))
    output(HRULE, color=COLOR_HINT)
    output()
    output("Welcome to kmd.\n", color=COLOR_HEADING)
    output()
    output(str(welcome), text_wrap=Wrap.WRAP_FULL)
    output(HRULE, color=COLOR_HINT)


@kmd_command
def help() -> None:
    """
    Show the kmd main help page.
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

    :param media: List media cache only.
    :param web: List web cache only.
    """
    if not media and not web:
        media = True
        web = True

    if media:
        files(global_settings().media_cache_dir)
        output()
    if web:
        files(global_settings().content_cache_dir)
        output()


@kmd_command
def cache_media(*urls: str) -> None:
    """
    Cache media at the given URLs in the media cache, using a tools for the appropriate
    service (yt-dlp for YouTube, Apple Podcasts, etc).
    """
    output()
    for url in urls:
        cached_paths = media_tools.cache_media(Url(url))
        output(f"{url}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
        for media_type, path in cached_paths.items():
            output(f"{media_type.name}: {fmt_path(path)}", text_wrap=Wrap.INDENT_ONLY)
        output()


@kmd_command
def cache_content(*urls_or_paths: str) -> None:
    """
    Cache the given file in the content cache. Downloads any URL or copies a local file.
    """
    output()
    for url_or_path in urls_or_paths:
        locator = as_url_or_path(url_or_path)
        cache_path, was_cached = file_cache_tools.cache_content(locator)
        cache_str = " (already cached)" if was_cached else ""
        output(f"{fmt_path(url_or_path)}{cache_str}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
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
            "What do you need help with? (Ask any question or press enter to see main `help` page.)",
            prompt_symbol=PROMPT_ASSIST,
        )
        if not input.strip():
            help()
            return
    with get_console().status("Thinking…", spinner=SPINNER):
        output_assistance(assistance(input))


@kmd_command
def assistant_system_message(skip_api: bool = False) -> CommandOutput:
    """
    Print the assistant system message.
    """

    item = Item(
        type=ItemType.export,
        title="Assistant System Message",
        format=Format.markdown,
        body=assist_system_message(skip_api=skip_api),
    )
    ws = current_workspace()
    store_path = ws.save(item, as_tmp=True)

    log.message("Saved assistant system message to %s", store_path)

    select(store_path)

    return CommandOutput(show_selection=True)


@kmd_command
def check_tools() -> None:
    """
    Check that all tools are installed.
    """
    output("Checking for recommended tools:")
    output()
    output(tool_check().formatted())
    output()


@kmd_command
def history(max: int = 30, raw: bool = False) -> None:
    """
    Show the command history for the current workspace.

    :param max: Show at most the last `max` commands.
    :param raw: Show raw command history by tailing the history file directly.
    """
    # TODO: Customize this by time frame.
    ws = current_workspace()
    history_file = ws.base_dir / ws.dirs.shell_history_yml
    chat_history = tail_chat_history(history_file, max)

    if raw:
        tail_file(history_file)
    else:
        n = len(chat_history.messages)
        for i, message in enumerate(chat_history.messages):
            output("% 4d: %s", i - n, message.content, text_wrap=Wrap.NONE)


@kmd_command
def clear_history() -> None:
    """
    Clear the command history for the current workspace. Old history file will be
    moved to the trash.
    """
    ws = current_workspace()
    history_file = ws.base_dir / ws.dirs.shell_history_yml
    trash(history_file)


@kmd_command
def init(path: Optional[str] = None) -> None:
    """
    Initialize a new workspace at the given path.
    """
    dir = Path(path) if path else Path(".")
    dirs = MetadataDirs(dir)
    if dirs.is_initialized():
        raise InvalidInput("Workspace already exists: %s", fmt_path(dir))
    if not dir.exists():
        dir.mkdir()
    dirs.initialize()

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

    return CommandOutput(show_selection=True)


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
def show(path: Optional[str] = None, console: bool = False, browser: bool = False) -> None:
    """
    Show the contents of a file if one is given, or the first file if multiple files
    are selected. Will try to use native apps or web browser to display the file if
    appropriate, and otherwise display the file in the console.

    Will use `bat` if available to show files in the console, including syntax
    highlighting and git diffs.

    :param console: Force display to console (not browser or native apps).
    :param browser: Force display to browser (not console or native apps).
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
                    local_path, _was_cached = cache_content(item.thumbnail_url)
                    terminal_show_image(local_path)
                except Exception as e:
                    log.info("Had trouble showing thumbnail image (will skip): %s", e)
                    output(f"[Image: {item.thumbnail_url}]", color=COLOR_HINT)

            view_file_native(ws.base_dir / input_path, use_console=console, use_browser=browser)
        else:
            view_file_native(input_path, use_console=console, use_browser=browser)
    except (InvalidInput, InvalidState):
        if path:
            # If path is absolute or we couldbn't get a selection, just show the file.
            view_file_native(path, use_console=console, use_browser=browser)
        else:
            raise InvalidInput("No selection")


@kmd_command
def cbcopy(path: Optional[str] = None, raw: bool = False) -> None:
    """
    Copy the contents of a file (or the first file in the selection) to the OS-native
    clipboard.

    :param raw: Copy the full exact contents of the file. Otherwise frontmatter is omitted.
    """
    import pyperclip

    input_paths = _assemble_paths(path)
    input_path = input_paths[0]

    format = detect_file_format(input_path)
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

    :param all: Normally edits only the first file given. This passes all files to the editor.
    """
    input_paths = _assemble_paths(path)
    if not all:
        input_paths = [input_paths[0]]

    edit_files(*input_paths)


@kmd_command
def save(
    parent: Optional[str] = None, to: Optional[str] = None, no_frontmatter: bool = False
) -> None:
    """
    Save the current selection to the given directory (which must exist), or to the
    current directory if no target given.

    :param parent: The directory to save the files to. If not given, it will be the current directory.
    :param to: If only one file is selected, a name to save it as. If it exists, it will overwrite (and make a backup).
    :param no_frontmatter: If true, will not include YAML frontmatter in the output.
    """
    ws = current_workspace()
    store_paths = ws.get_selection()

    def copy_file(store_path: StorePath, target_path: Path):
        log.message("Saving: %s -> %s", store_path, target_path)
        copyfile_atomic(ws.base_dir / store_path, target_path, backup_suffix=".bak")
        if no_frontmatter:
            fmf_strip_frontmatter(target_path)

    if len(store_paths) == 1 and to:
        target_path = Path(to)
        store_path = store_paths[0]
        copy_file(store_path, target_path)
    else:
        target_dir = Path(parent) if parent else Path(".")
        if not target_dir.exists():
            raise InvalidInput(f"Target directory does not exist: {target_dir}")

        for store_path in store_paths:
            target_path = target_dir / basename(store_path)
            copy_file(store_path, target_path)


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


def _dual_format_size(size: int):
    readable_size_str = ""
    if size > 1000000:
        readable_size = naturalsize(size).replace("Bytes", "B")
        readable_size_str += f" ({readable_size})"
    return f"{size} bytes{readable_size_str}"


@kmd_command
def file_info(
    *paths: str, slow: bool = False, size_summary: bool = False, format: bool = False
) -> None:
    """
    Show info about a file. By default this includes a summary of the size and HTML
    structure of the items at the given paths (for text documents) and the detected
    mime type.

    :param slow: Normally uses a fast, approximate method to count sentences.
    This enables slower Spacy sentence segmentation.
    :param size_summary: Only show size summary (words, sentences, paragraphs for a text document).
    :param mime_type: Only show detected mime type.
    """
    if not size_summary and not format:
        size_summary = format = True

    input_paths = _assemble_paths(*paths)
    output()
    for input_path in input_paths:
        output(f"{fmt_path(input_path)}:", color=COLOR_EMPH)

        if format:
            mime_type_str = detect_mime_type(input_path) or "unknown"
            output(f"{mime_type_str}", text_wrap=Wrap.INDENT_ONLY)

        size = Path(input_path).stat().st_size
        output(_dual_format_size(size), text_wrap=Wrap.INDENT_ONLY)

        try:
            _frontmatter_str, offset = fmf_read_frontmatter_raw(input_path)
            if offset:
                output(f"frontmatter: {_dual_format_size(offset)}", text_wrap=Wrap.INDENT_ONLY)
        except UnicodeDecodeError:
            pass

        if size_summary and mime_type_str.startswith("text"):
            body, frontmatter = fmf_read(input_path)

            if body:
                parsed_body = parse_divs(body)
                size_summary_str = parsed_body.size_summary(fast=not slow)
                output(f"body: {size_summary_str}", text_wrap=Wrap.INDENT_ONLY)
            else:
                output("No text body", text_wrap=Wrap.INDENT_ONLY)

        output()


@kmd_command
def relations(*paths: str) -> None:
    """
    Show the relations for the current selection.
    """
    input_paths = _assemble_paths(*paths)

    output()
    for input_path in input_paths:
        item = current_workspace().load(StorePath(input_path))
        output(f"{fmt_path(not_none(item.store_path))}:", color=COLOR_EMPH)
        relations = item.relations.__dict__ if item.relations else {}
        if any(relations.values()):
            output(to_yaml_string(relations), text_wrap=Wrap.INDENT_ONLY)
        else:
            output("(no relations)", text_wrap=Wrap.INDENT_ONLY)
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
                raise InvalidInput(
                    f"Unrecognized value for parameter `{key}` (type {param.type.__name__}): `{value}`"
                )

        current_vals = ws.get_param_values()
        new_params = {**current_vals.values, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        ws.set_param(new_params)

    output_heading("Available Parameters")

    for param in USER_SETTABLE_PARAMS.values():
        output(format_name_and_description(param.name, param.full_description))
        output()

    param_values = ws.get_param_values()
    if not param_values.values:
        output_status("No parameters are set.")
    else:
        output_heading("Current Parameters")
        for key, value in param_values.items():
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
def log_level(level: Optional[str] = None, console: bool = False, file: bool = False) -> None:
    """
    Set or show the log level. Applies to both console and file log levels unless specified.

    :param level: The log level to set. If not specified, will show current level.
    :param console: Set console log level only.
    :param file: Set file log level only.
    """
    if not console and not file:
        console = True
        file = True

    if level:
        level_parsed = LogLevel.parse(level)
        with update_global_settings() as settings:
            if console:
                settings.console_log_level = level_parsed
            if file:
                settings.file_log_level = level_parsed

        reset_logging()

    output()
    output(format_name_and_description("file_log_level", global_settings().file_log_level.name))
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
    archive_dir = ws.base_dir / ws.dirs.archive_dir
    trash(archive_dir)
    os.makedirs(archive_dir, exist_ok=True)


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

    :param brief: Show only action names. Otherwise show actions and descriptions.
    :param all: Include actions with no preconditions.
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

    for precondition in all_preconditions():
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

    :param summary: Show only summary of number of files in each folder.
    :param iso_time: Show time in ISO format.
    """
    if len(paths) == 0:
        paths_to_show = [Path(".")]
    else:
        paths_to_show = [Path(path) for path in paths]

    ws_dirs, is_sandbox = current_workspace_info()
    ws_base_dir = ws_dirs.base_dir if ws_dirs else None
    relative_to = ws_base_dir if ws_base_dir and not is_sandbox else Path(".")

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
    Useful to find all docs or resources matching a string or regex. This wraps
    ripgrep.

    Example: Look for all resource files containing the string "youtube.com",
    sorted by date modified:

    search "youtube.com" resources/ --sort=modified

    :param sort: How to sort results. Can be `path` or `modified` or `created` (as with `rg`).
    :param ignore_case: Ignore case when searching.
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

    :param concepts_only: Show only concepts.
    :param resources_only: Show only resources.
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

    :param inplace: Overwrite the original file. Otherwise save to a new
    file with `_formatted` appended to the original name.
    """
    for path in paths:
        target_path = None
        dirname, name, item_type, ext = split_filename(path)
        new_name = f"{name}_formatted"
        target_path = join_filename(dirname, new_name, item_type, ext)

        normalize_text_file(path, target_path=target_path)
        if inplace:
            trash(path)
            os.rename(target_path, path)
            output_status("Formatted:\n%s", fmt_lines([fmt_path(path)]))
        else:
            output_status(
                "Formatted:\n%s", fmt_lines([f"{fmt_path(path)} -> {fmt_path(target_path)}"])
            )


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
