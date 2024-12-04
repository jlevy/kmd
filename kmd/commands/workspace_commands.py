import os
from pathlib import Path
from typing import Optional

from frontmatter_format import to_yaml_string
from rich.text import Text

from kmd.action_defs import load_all_actions
from kmd.commands.command_registry import kmd_command
from kmd.commands.files_commands import files, show, trash
from kmd.commands.selection_commands import select
from kmd.config.logger import get_logger
from kmd.config.settings import global_settings
from kmd.config.text_styles import COLOR_EMPH, COLOR_HINT, COLOR_SUGGESTION, EMOJI_TRUE, EMOJI_WARN
from kmd.errors import InvalidInput, InvalidOperation
from kmd.exec.resolve_args import (
    assemble_path_args,
    assemble_store_path_args,
    import_locator_args,
    resolve_locator_arg,
)
from kmd.file_formats.chat_format import tail_chat_history
from kmd.file_storage.metadata_dirs import MetadataDirs
from kmd.lang_tools.inflection import plural
from kmd.media import media_tools
from kmd.model.args_model import fmt_loc
from kmd.model.items_model import ItemType
from kmd.model.params_model import USER_SETTABLE_PARAMS
from kmd.model.paths_model import fmt_store_path, StorePath
from kmd.model.shell_model import ShellResult
from kmd.preconditions import all_preconditions
from kmd.preconditions.precondition_checks import actions_matching_paths
from kmd.server.local_url_formatters import local_url_formatter
from kmd.shell.shell_output import (
    cprint,
    format_name_and_description,
    print_heading,
    print_status,
    Wrap,
)
from kmd.shell_tools.git_tools import add_to_git_ignore
from kmd.shell_tools.native_tools import tail_file
from kmd.text_docs.unified_diffs import unified_diff_items
from kmd.util.format_utils import fmt_lines
from kmd.util.obj_utils import remove_values
from kmd.util.parse_key_vals import format_key_value, parse_key_value
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from kmd.web_content.file_cache_tools import cache_file
from kmd.workspaces.workspace_names import check_strict_workspace_name
from kmd.workspaces.workspaces import (
    current_workspace,
    get_sandbox_workspace,
    resolve_workspace,
    sandbox_dir,
)

log = get_logger(__name__)


@kmd_command
def clear_sandbox() -> None:
    """
    Clear the entire sandbox by moving it to the trash.
    Use with caution!
    """
    trash(sandbox_dir())
    ws = get_sandbox_workspace()
    ws.reload()
    ws.log_store_info()


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
        cprint()
    if web:
        files(global_settings().content_cache_dir)
        cprint()


@kmd_command
def cache_media(*urls: str) -> None:
    """
    Cache media at the given URLs in the media cache, using a tools for the appropriate
    service (yt-dlp for YouTube, Apple Podcasts, etc).
    """
    cprint()
    for url in urls:
        cached_paths = media_tools.cache_media(Url(url))
        cprint(f"{url}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
        for media_type, path in cached_paths.items():
            cprint(f"{media_type.name}: {fmt_loc(path)}", text_wrap=Wrap.INDENT_ONLY)
        cprint()


@kmd_command
def cache_content(*urls_or_paths: str) -> None:
    """
    Cache the given file in the content cache. Downloads any URL or copies a local file.
    """
    cprint()
    for url_or_path in urls_or_paths:
        locator = resolve_locator_arg(url_or_path)
        cache_path, was_cached = cache_file(locator)
        cache_str = " (already cached)" if was_cached else ""
        cprint(f"{fmt_loc(url_or_path)}{cache_str}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
        cprint(f"{cache_path}", text_wrap=Wrap.INDENT_ONLY)
        cprint()


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
            cprint(
                Text("% 4d:" % (i - n), style=COLOR_HINT)
                + Text(f" `{message.content}`", style=COLOR_SUGGESTION),
                text_wrap=Wrap.NONE,
            )


@kmd_command
def clear_history() -> None:
    """
    Clear the command history for the current workspace. Old history file will be
    moved to the trash.
    """
    ws = current_workspace()
    trash(ws.base_dir / ws.dirs.shell_history_yml)


@kmd_command
def init(path: Optional[str] = None) -> None:
    """
    Initialize a new workspace at the given path, or in the current directory if no path given.
    Idempotent.
    """
    dir = Path(path) if path else Path(".")
    dirs = MetadataDirs(dir)
    if dirs.is_initialized():
        log.warning("Workspace metadata already initialized: %s", fmt_loc(dirs.dot_dir))
    else:
        if not dir.exists():
            dir.mkdir()
        dirs.initialize()

    add_to_git_ignore(dir, [".kmd/"])

    current_workspace(silent=True).log_store_info()


@kmd_command
def workspace(workspace_name: Optional[str] = None) -> None:
    """
    Show info on the current workspace (if no arg given), or switch to a new workspace,
    creating it if it doesn't exist. Equivalent to `mkdir some_name.kb`.
    """
    if workspace_name:
        ws_name, ws_path, is_sandbox = resolve_workspace(workspace_name)
        if not ws_path.exists():
            # Enforce reasonable naming on new workspaces.
            ws_name = check_strict_workspace_name(ws_name)

        os.makedirs(ws_path, exist_ok=True)
        os.chdir(ws_path)
        print_status(f"Changed to workspace: {ws_name} ({ws_path})")

    current_workspace(silent=True).log_store_info()


@kmd_command
def reload_workspace() -> None:
    """
    Reload the current workspace. Helpful for debugging to reset in-memory state.
    """
    current_workspace().reload()


@kmd_command
def item_id(*paths: str) -> None:
    """
    Show the item id for the given paths. This is the unique identifier that is used to
    determine if two items are the same, so action results are cached.
    """
    input_paths = assemble_path_args(*paths)
    for path in input_paths:
        item = current_workspace().load(StorePath(path))
        id = item.item_id()
        cprint(
            format_name_and_description(fmt_loc(path), str(id), text_wrap=Wrap.INDENT_ONLY),
            text_wrap=Wrap.NONE,
        )
        cprint()


# FIXME: Make sure fallback to regular file diff works.
@kmd_command
def diff(*paths: str, stat: bool = False, save: bool = False, strict: bool = False) -> ShellResult:
    """
    Show the unified diff between the given files. It's helpful to maintain metadata on
    diffs, so we only support diffing stored items. But the sandbox can be used for
    files not in another store.

    :param stat: Only show the diffstat summary.
    :param strict: If true, will abort if the items are of different formats.
    """
    ws = current_workspace()
    if len(paths) == 2:
        [path1, path2] = paths
    else:
        try:
            last_selections = ws.selections.previous_n(2, expected_size=1)
        except InvalidOperation:
            raise InvalidInput(
                "Need two selections of single files in history or exactly two paths to diff"
            )
        [path1] = last_selections[0].paths
        [path2] = last_selections[1].paths

    [store_path1, store_path2] = import_locator_args(path1, path2)
    item1, item2 = ws.load(store_path1), ws.load(store_path2)

    diff_item = unified_diff_items(item1, item2, strict=strict)

    if stat:
        cprint(diff.diffstat, text_wrap=Wrap.NONE)
        return ShellResult(show_selection=False)
    elif save:
        diff_store_path = ws.save(diff_item, as_tmp=False)
        select(diff_store_path)
        return ShellResult(show_selection=True)
    else:
        diff_store_path = ws.save(diff_item, as_tmp=True)
        show(diff_store_path)
        return ShellResult(show_selection=False)


@kmd_command
def relations(*paths: str) -> None:
    """
    Show the relations for the current selection, including items that are upstream,
    like the items this item is derived from.
    """
    input_paths = assemble_path_args(*paths)

    cprint()
    for input_path in input_paths:
        item = current_workspace().load(StorePath(input_path))
        cprint(f"{fmt_store_path(not_none(item.store_path))}:", color=COLOR_EMPH)
        relations = item.relations.__dict__ if item.relations else {}
        if any(relations.values()):
            cprint(to_yaml_string(relations), text_wrap=Wrap.INDENT_ONLY)
        else:
            cprint("(no relations)", text_wrap=Wrap.INDENT_ONLY)
        cprint()


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

        current_vals = ws.params.get_values()
        new_params = {**current_vals.values, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        ws.params.set(new_params)

    print_heading("Available Parameters")

    for param in USER_SETTABLE_PARAMS.values():
        cprint(format_name_and_description(param.name, param.full_description))
        cprint()

    param_values = ws.params.get_values()
    if not param_values.values:
        print_status("No parameters are set.")
    else:
        print_heading("Current Parameters")
        for key, value in param_values.items():
            cprint(format_key_value(key, value))
        cprint()


@kmd_command
def import_item(
    *files_or_urls: str, type: Optional[ItemType] = None, inplace: bool = False
) -> ShellResult:
    """
    Add a file or URL resource to the workspace as an item, with associated metadata.

    :param inplace: If set and the item is already in the store, reimport the item,
      adding or rewriting metadata frontmatter.
    :param type: Change the item type. Usually items are auto-detected from the file
      format (typically doc or resource), but you can override this with this option.
    """
    if not files_or_urls:
        raise InvalidInput("No files or URLs provided to import")

    ws = current_workspace()
    store_paths = []

    locators = [resolve_locator_arg(r) for r in files_or_urls]
    store_paths = ws.import_items(*locators, as_type=type, reimport=inplace)

    print_status(
        "Imported %s %s:\n%s",
        len(store_paths),
        plural("item", len(store_paths)),
        fmt_lines(store_paths),
    )
    select(*store_paths)

    return ShellResult(show_selection=True)


@kmd_command
def archive(*paths: str) -> None:
    """
    Archive the items at the given path, or the current selection.
    """
    store_paths = assemble_store_path_args(*paths)
    ws = current_workspace()
    archived_paths = [ws.archive(store_path) for store_path in store_paths]

    print_status(f"Archived:\n{fmt_lines(fmt_loc(p) for p in archived_paths)}")
    select()


@kmd_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    ws = current_workspace()
    store_paths = assemble_store_path_args(*paths)
    unarchived_paths = [ws.unarchive(store_path) for store_path in store_paths]

    print_status(f"Unarchived:\n{fmt_lines(fmt_loc(p) for p in unarchived_paths)}")


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
    store_paths = assemble_store_path_args(*paths)
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
        cprint("No applicable actions for selection.")
        return
    with local_url_formatter(ws.name) as fmt:
        if brief:
            action_names = [action.name for action in applicable_actions]
            cprint("Applicable actions:", color=COLOR_SUGGESTION)
            cprint(
                Text.join(
                    Text(", ", style=COLOR_HINT),
                    (fmt.command_link(name) for name in action_names),
                ),
                extra_indent="    ",
            )
            cprint()
        else:
            cprint(
                "Applicable actions for items:\n%s",
                fmt_lines(store_paths),
                color=COLOR_SUGGESTION,
                text_wrap=Wrap.NONE,
            )
            cprint()
            for action in applicable_actions:
                precondition_str = (
                    f"(matches precondition {action.precondition })"
                    if action.precondition
                    else "(no precondition)"
                )
                cprint(
                    format_name_and_description(
                        fmt.command_link(action.name),
                        action.description,
                        extra_note=precondition_str,
                    ),
                )
                cprint()


@kmd_command
def preconditions() -> None:
    """
    List all preconditions and if the current selection meets them.
    """

    ws = current_workspace()
    selection = ws.selections.current.paths
    if not selection:
        raise InvalidInput("No selection")

    items = [ws.load(item) for item in selection]

    print_status("Precondition check for selection:\n %s", fmt_lines(selection))

    for precondition in all_preconditions():
        satisfied = all(precondition(item) for item in items)
        emoji = EMOJI_TRUE if satisfied else " "
        satisfied_str = "satisfied" if satisfied else "not satisfied"
        cprint(f"{emoji} {precondition} {satisfied_str}", text_wrap=Wrap.NONE)

    cprint()


@kmd_command
def normalize(*paths: str) -> ShellResult:
    """
    Normalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    # TODO: Make a version of this that works outside the workspace on Markdown files,
    # (or another version just called `format` that does this).
    ws = current_workspace()
    store_paths = assemble_store_path_args(*paths)

    canon_paths = []
    for store_path in store_paths:
        log.message("Canonicalizing: %s", fmt_loc(store_path))
        for item_store_path in ws.walk_items(store_path):
            try:
                ws.normalize(item_store_path)
            except InvalidInput as e:
                log.warning(
                    "%s Could not canonicalize %s: %s",
                    EMOJI_WARN,
                    fmt_loc(item_store_path),
                    e,
                )
            canon_paths.append(item_store_path)

    # TODO: Also consider implementing duplicate elimination here.

    if len(canon_paths) > 0:
        select(*canon_paths)
    return ShellResult(show_selection=len(canon_paths) > 0)
