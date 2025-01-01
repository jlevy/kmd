import os
from datetime import datetime, timezone
from os.path import basename
from pathlib import Path
from typing import cast, List, Optional

from frontmatter_format import fmf_read_raw, fmf_strip_frontmatter
from rich.text import Text

from kmd.commands.command_registry import kmd_command
from kmd.commands.selection_commands import select
from kmd.config.logger import get_logger
from kmd.config.text_styles import COLOR_EMPH, COLOR_EMPH_ALT, COLOR_HINT, EMOJI_WARN
from kmd.errors import InvalidInput, InvalidOperation, InvalidState
from kmd.exec.resolve_args import (
    assemble_path_args,
    import_locator_args,
    resolvable_paths,
    resolve_path_arg,
)
from kmd.file_formats.doc_normalization import normalize_text_file
from kmd.file_tools.file_sort_filter import (
    collect_files,
    FileInfo,
    FileListing,
    GroupByOption,
    parse_since,
    SortOption,
    type_suffix,
)
from kmd.file_tools.ignore_files import ignore_none
from kmd.model.args_model import fmt_loc
from kmd.model.file_formats_model import detect_file_format, Format, join_filename, split_filename
from kmd.model.items_model import Item, ItemType
from kmd.model.paths_model import parse_path_spec, StorePath
from kmd.model.shell_model import ShellResult
from kmd.server.local_url_formatters import local_url_formatter
from kmd.shell.shell_file_info import print_file_info
from kmd.shell.shell_output import console_pager, cprint, print_status, print_style, Style, Wrap
from kmd.shell_tools.native_tools import (
    edit_files,
    native_trash,
    terminal_show_image,
    view_file_native,
    ViewMode,
)
from kmd.shell_tools.tool_deps import Tool, tool_check
from kmd.text_docs.unified_diffs import unified_diff_files, unified_diff_items
from kmd.util.format_utils import fmt_lines, fmt_size_human, fmt_time
from kmd.util.parse_shell_args import shell_quote
from kmd.util.strif import copyfile_atomic
from kmd.web_content.file_cache_tools import cache_file
from kmd.workspaces.workspaces import current_ignore, current_workspace

log = get_logger(__name__)


@kmd_command
def show(
    path: Optional[str] = None,
    console: bool = False,
    native: bool = False,
    thumbnail: bool = False,
    browser: bool = False,
) -> None:
    """
    Show the contents of a file if one is given, or the first file if multiple files
    are selected. Will try to use native apps or web browser to display the file if
    appropriate, and otherwise display the file in the console.

    Will use `bat` if available to show files in the console, including syntax
    highlighting and git diffs.

    :param console: Force display to console (not browser or native apps).
    :param native: Force display with a native app (depending on your system configuration).
    :param thumbnail: If there is a thumbnail image, show it too.
    :param browser: Force display with your default web browser.
    """
    view_mode = (
        ViewMode.console
        if console
        else ViewMode.browser if browser else ViewMode.native if native else ViewMode.auto
    )
    try:
        input_paths = assemble_path_args(path)
        input_path = input_paths[0]

        if isinstance(input_path, StorePath):
            ws = current_workspace()
            if input_path.is_file():
                # Optionally, if we can inline display the image (like in kitty) above the text representation, do that.
                item = ws.load(input_path)
                if thumbnail and item.thumbnail_url:
                    try:
                        local_path, _was_cached = cache_file(item.thumbnail_url)
                        terminal_show_image(local_path)
                    except Exception as e:
                        log.info("Had trouble showing thumbnail image (will skip): %s", e)
                        cprint(f"[Image: {item.thumbnail_url}]", color=COLOR_HINT)

            view_file_native(ws.base_dir / input_path, view_mode=view_mode)
        else:
            view_file_native(input_path, view_mode=view_mode)
    except (InvalidInput, InvalidState):
        if path:
            # If path is absolute or we couldbn't get a selection, just show the file.
            view_file_native(path, view_mode=view_mode)
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

    input_paths = assemble_path_args(path)
    input_path = input_paths[0]

    format = detect_file_format(input_path)
    if not format or not format.is_text:
        raise InvalidInput(f"Cannot copy non-text files to clipboard: {fmt_loc(input_path)}")

    if raw:
        with open(input_path, "r") as f:
            content = f.read()

        pyperclip.copy(content)
        print_status(
            "Copied raw contents of file to clipboard (%s chars):\n%s",
            len(content),
            fmt_lines([fmt_loc(input_path)]),
        )
    else:
        content, metadata_str = fmf_read_raw(input_path)
        pyperclip.copy(content)
        skip_msg = ""
        if metadata_str:
            skip_msg = f", skipping {len(metadata_str)} chars of frontmatter"
        print_status(
            "Copied contents of file to clipboard (%s chars%s):\n%s",
            len(content),
            skip_msg,
            fmt_lines([fmt_loc(input_path)]),
        )


@kmd_command
def edit(path: Optional[str] = None, all: bool = False) -> None:
    """
    Edit the contents of a file using the user's default editor (or defaulting to nano).

    :param all: Normally edits only the first file given. This passes all files to the editor.
    """
    input_paths = assemble_path_args(path)
    if not all:
        input_paths = [input_paths[0]]

    edit_files(*input_paths)


@kmd_command
def save(
    parent: Optional[str] = None, to: Optional[str] = None, no_frontmatter: bool = False
) -> None:
    """
    Save the current selection to the given directory, or to the current directory if no
    target given.

    :param parent: The directory to save the files to. If not given, it will be the
        current directory.
    :param to: If only one file is selected, a name to save it as. If it exists, it will
        overwrite (and make a backup).
    :param no_frontmatter: If true, will not include YAML frontmatter in the output.
    """
    ws = current_workspace()
    store_paths = ws.selections.current.paths

    def copy_file(store_path: StorePath, target_path: Path):
        path = ws.base_dir / store_path
        log.message("Saving: %s -> %s", fmt_loc(path), fmt_loc(target_path))
        copyfile_atomic(path, target_path, backup_suffix=".bak", make_parents=True)
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
    input_paths = assemble_path_args(*paths)

    for path in input_paths:
        log.message("Stripping frontmatter from: %s", fmt_loc(path))
        fmf_strip_frontmatter(path)


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
    :param format: Only show detected file format.
    """
    if not size_summary and not format:
        size_summary = format = True

    # FIXME: Ensure this yields absolute paths for sandbox store paths
    input_paths = assemble_path_args(*paths)
    for input_path in input_paths:
        cprint(f"{fmt_loc(input_path)}:", color=COLOR_EMPH, text_wrap=Wrap.NONE)
        with print_style(Style.INDENT):
            print_file_info(
                input_path, slow=slow, show_size_details=size_summary, show_format=format
            )
        cprint()


@kmd_command
def rename(path: str, new_path: str) -> None:
    """
    Rename a file or item. Creates any new parent paths as needed.
    Note this may invalidate relations that point to the old store path.

    TODO: Add an option here to update all relations in the workspace.
    """
    from_path, to_path = assemble_path_args(path, new_path)
    to_path.parent.mkdir(parents=True, exist_ok=True)
    os.rename(from_path, to_path)

    print_status(f"Renamed: {fmt_loc(from_path)} -> {fmt_loc(to_path)}")


@kmd_command
def copy(*paths: str) -> None:
    """
    Copy the items at the given paths to the target path.
    """
    if len(paths) < 2:
        raise InvalidInput("Must provide at least one source path and a target path")

    src_paths = [resolve_path_arg(path) for path in paths[:-1] if path]
    dest_path = resolve_path_arg(paths[-1])

    if len(src_paths) == 1 and dest_path.is_dir():
        dest_path = dest_path / src_paths[0].name
    elif len(src_paths) > 1 and not dest_path.is_dir():
        raise InvalidInput(f"Cannot copy multiple files to a file target: {dest_path}")

    for src_path in src_paths:
        copyfile_atomic(src_path, dest_path, make_parents=True)

    print_status(
        f"Copied:\n{fmt_lines(fmt_loc(p) for p in src_paths)}\n->\n{fmt_lines([fmt_loc(dest_path)])}",
    )


@kmd_command
def trash(*paths: str) -> None:
    """
    Trash the items at the given paths. Uses OS-native trash or recycle bin on Mac, Windows, or Linux.
    """

    resolved_paths = assemble_path_args(*paths)
    native_trash(*resolved_paths)
    print_status(f"Deleted (check trash or recycling bin to recover):\n{fmt_lines(resolved_paths)}")


def _print_listing_tallies(
    file_listing: FileListing,
    total_displayed: int,
    total_displayed_size: int,
    max_files: int,
    max_depth: int,
    max_per_subdir: int,
) -> None:
    if total_displayed > 0:
        cprint(
            f"{total_displayed} files ({fmt_size_human(total_displayed_size)}) shown",
            color=COLOR_EMPH,
        )
    if file_listing.files_total > file_listing.files_matching > total_displayed:
        cprint(
            f"of {file_listing.files_matching} files "
            f"({fmt_size_human(file_listing.size_matching)}) matching criteria",
            color=COLOR_EMPH,
        )
    if file_listing.files_total > total_displayed:
        cprint(
            f"from {file_listing.files_total} total files "
            f"({fmt_size_human(file_listing.size_total)})",
            color=COLOR_EMPH,
        )
    if file_listing.total_ignored > 0:
        cprint(f"{EMOJI_WARN} {file_listing.total_ignored} files were ignored", color=COLOR_EMPH)
        cprint("(use --no_ignore to show hidden files)", color=COLOR_HINT)

    if file_listing.total_skipped > 0:
        cprint(
            f"{EMOJI_WARN} long file listing: capped "
            f"at max_files={max_files}, max_depth={max_depth}, max_per_subdir={max_per_subdir}",
            color=COLOR_EMPH,
        )
        cprint("(use --no_max to remove cutoff)", color=COLOR_HINT)


@kmd_command
def files(
    *paths: str,
    brief: bool = False,
    recent: bool = False,
    flat: bool = False,
    pager: bool = False,
    include_dirs: bool = False,
    max_per_group: int = 0,
    depth: int = 3,
    max_per_subdir: int = 1000,
    max_files: int = 1000,
    no_max: bool = False,
    no_ignore: bool = False,
    all: bool = False,
    save: bool = False,
    sort: Optional[SortOption] = None,
    reverse: bool = False,
    since: Optional[str] = None,
    groupby: Optional[GroupByOption] = GroupByOption.parent,
    iso_time: bool = False,
) -> ShellResult:
    """
    List files or folders in the current directory or specified paths. Lists recursively
    by default.

    For a quick, paged overview of all files in a big directory, use `files --pager`.

    :param brief: Only shows a few files per directory.
        Same as `--groupby=parent --max_per_group=10 `.
    :param recent: Only shows the most recently modified files in each directory.
        Same as `--sort=modified --reverse --groupby=parent --max_per_group=10`.
    :param flat: Show files in a flat list, rather than grouped by parent directory.
        Same as `--groupby=flat`.
    :param pager: Use the pager when displaying the output.
    :param depth: Maximum depth to recurse into directories. -1 means no limit.
    :param max_files_per_subdir: Maximum number of files to yield per subdirectory
        (not including the top level). -1 means no limit.
    :param max_files: Maximum number of files to yield per input path.
        -1 means no limit.
    :param max_per_group: Limit the first number of items displayed per group
        (if groupby is used) or in total. 0 means show all.
    :param no_max: Disable limits on depth and number of files. Same as
        `--max_depth=-1 --max_per_subdir=-1 --max_files=-1`.
    :param no_ignore: Disable ignoring hidden files.
    :param all: Same as `--no_ignore --no_max`.
    :param save: Save the listing as a CSV file item.
    :param sort: Sort by 'filename','size', 'accessed', 'created', or 'modified'.
    :param reverse: Reverse the sorting order.
    :param since: Filter files modified since a given time (e.g., '1 day', '2 hours').
    :param groupby: Group results. Can be 'flat' (no grouping), 'parent', or 'suffix'.
         Defaults to 'parent'.
    :param iso_time: Show time in ISO format (default is human-readable age).
    """
    # TODO: Add a --full option with line and word counts and file_info details
    # and also include these in --save.

    if len(paths) == 0:
        paths_to_show = [Path(".")]
    else:
        paths_to_show = [parse_path_spec(path) for path in paths]

    if brief or recent:
        if max_per_group <= 0:
            max_per_group = 10
        if groupby is None:
            groupby = GroupByOption.parent
    if recent:
        if sort is None:
            sort = SortOption.modified
            reverse = True
    if flat:
        groupby = GroupByOption.flat

    if all:
        no_ignore = True
        no_max = True
    if no_max:
        depth = max_per_subdir = max_files = -1

    since_seconds = parse_since(since) if since else 0.0

    # Determine whether to show hidden files for this path.
    is_ignored = ignore_none if no_ignore else current_ignore()
    for path in paths_to_show:
        log.info("Checking ignore for %s", fmt_loc(path))
        if not no_ignore and is_ignored(path, is_dir=path.is_dir()):
            log.info(
                "Requested path is on the ignore list so disabling ignore: %s",
                fmt_loc(path),
            )
            is_ignored = ignore_none
            break

    base_path = Path(".")

    # Collect all the files.
    file_listing = collect_files(
        start_paths=paths_to_show,
        ignore=is_ignored,
        since_seconds=since_seconds,
        base_path=base_path,
        max_depth=depth,
        max_files_per_subdir=max_per_subdir,
        max_files_total=max_files,
        include_dirs=include_dirs,
    )

    ws = current_workspace()

    # Check if this listing is within the current workspace.
    active_ws_name = ws.name if base_path.resolve().is_relative_to(ws.base_dir.resolve()) else None
    base_is_ws = ws.base_dir.resolve() == base_path.resolve()

    log.info("Collected %s files.", file_listing.files_total)

    if not file_listing.files:
        cprint("No files found.")
        _print_listing_tallies(file_listing, 0, 0, max_files, depth, max_per_subdir)
        return ShellResult()

    df = file_listing.as_dataframe()

    if sort:
        # Determine the primary and secondary sort columns.
        primary_sort = sort.value
        secondary_sort = "filename" if primary_sort != "filename" else "created"

        df.sort_values(
            by=[primary_sort, secondary_sort], ascending=[not reverse, True], inplace=True
        )

    items_matching = len(df)
    log.info(f"Total items collected: {items_matching}")

    if groupby and groupby != GroupByOption.flat:
        grouped = df.groupby(groupby.value)
    else:
        grouped = [(None, df)]

    if save:
        item = Item(
            type=ItemType.export,
            title="File Listing",
            description=f"Files in {', '.join(fmt_loc(p) for p in paths_to_show)}",
            format=Format.csv,
            body=df.to_csv(index=False),
        )
        ws = current_workspace()
        store_path = ws.save(item, as_tmp=False)
        log.message("File listing saved to: %s", fmt_loc(store_path))

        select(store_path)

        return ShellResult(show_selection=True)

    total_displayed = 0
    total_displayed_size = 0
    now = datetime.now(timezone.utc)

    # Define spacing constants.
    TIME_WIDTH = 12
    SIZE_WIDTH = 8
    SPACING = "  "
    indent = " " * (TIME_WIDTH + SIZE_WIDTH + len(SPACING) * 2)

    with console_pager(use_pager=pager):
        with local_url_formatter(active_ws_name) as fmt:
            for group_name, group_df in grouped:
                if group_name:
                    cprint(f"\n{group_name} ({len(group_df)} files)", color=COLOR_EMPH)

                if max_per_group:
                    display_df = group_df.head(max_per_group)
                else:
                    display_df = group_df

                for row in display_df.itertuples(index=False, name="FileInfo"):
                    row = cast(FileInfo, row)
                    short_file_size = fmt_size_human(row.size)
                    full_file_size = f"{row.size} bytes"
                    short_mod_time = fmt_time(row.modified, iso_time=iso_time, now=now, brief=True)
                    full_mod_time = fmt_time(row.modified, friendly=True, now=now)

                    rel_path = str(row.relative_path)

                    # If we are listing from within a workspace and we are at the base
                    # of the workspace, we include the paths as store paths (with an @
                    # prefix). Otherwise, use regular paths.
                    if active_ws_name and base_is_ws:
                        display_path = StorePath(rel_path)  # Add a local server link.
                        display_path_str = f"{display_path.display_str()}{type_suffix(row)}"
                    else:
                        display_path = Path(rel_path)
                        display_path_str = f"{display_path}{type_suffix(row)}"

                    # Assemble output line.
                    # FIXME: Restore coloring on mod time and size.
                    line = Text()
                    line.append(
                        fmt.tooltip_link(short_mod_time.rjust(TIME_WIDTH), tooltip=full_mod_time)
                    )
                    line.append(SPACING)
                    line.append(
                        fmt.tooltip_link(short_file_size.rjust(SIZE_WIDTH), tooltip=full_file_size)
                    )
                    line.append(SPACING)
                    line.append(
                        fmt.path_link(
                            display_path,
                            link_text=display_path_str,
                        ),
                    )

                    cprint(line, text_wrap=Wrap.NONE)
                    total_displayed += 1
                    total_displayed_size += row.size

                # Indicate if items are omitted.
                if groupby and max_per_group and len(group_df) > max_per_group:
                    cprint(
                        f"{indent}… and {len(group_df) - max_per_group} more files",
                        color=COLOR_EMPH_ALT,
                        text_wrap=Wrap.NONE,
                    )
                cprint()

            if not groupby and max_per_group and items_matching > max_per_group:
                cprint(
                    f"{indent}… and {items_matching - max_per_group} more files",
                    color=COLOR_EMPH_ALT,
                    text_wrap=Wrap.NONE,
                )

            _print_listing_tallies(
                file_listing,
                total_displayed,
                total_displayed_size,
                max_files,
                depth,
                max_per_subdir,
            )

    return ShellResult()


@kmd_command
def search(
    query_str: str,
    *paths: str,
    sort: str = "path",
    ignore_case: bool = False,
    verbose: bool = False,
) -> ShellResult:
    """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex. This wraps
    ripgrep.

    Example: Look for all resource files containing the string "youtube.com",
    sorted by date modified:

    search "youtube.com" resources/ --sort=modified

    :param sort: How to sort results. Can be `path` or `modified` or `created` (as with `rg`).
    :param ignore_case: Ignore case when searching.
    :param verbose: Also print the ripgrep command line.
    """
    tool_check().require(Tool.ripgrep)
    from ripgrepy import RipGrepNotFound, Ripgrepy

    resolved_paths = assemble_path_args(*paths)

    strip_prefix = None
    if not resolved_paths:
        resolved_paths = (Path("."),)
        strip_prefix = "./"
    try:
        rg = Ripgrepy(query_str, *[str(p) for p in resolved_paths])
        rg = rg.files_with_matches().sort(sort)
        if ignore_case:
            rg = rg.ignore_case()
        if verbose:
            command = " ".join(
                [shell_quote(arg) for arg in rg.command]
                + [query_str]
                + [str(p) for p in resolved_paths]
            )
            cprint(f"{command}")
        rg_output = rg.run().as_string
        results: List[str] = [
            line.lstrip(strip_prefix) if strip_prefix and line.startswith(strip_prefix) else line
            for line in rg_output.splitlines()
        ]

        return ShellResult(results, show_result=True)
    except RipGrepNotFound:
        raise InvalidState("`rg` command not found. Install ripgrep to use the search command.")


@kmd_command
def reformat(*paths: str, inplace: bool = False) -> ShellResult:
    """
    Format text, Markdown, or HTML according to kmd conventions.

    TODO: Also handle JSON and YAML.

    :param inplace: Overwrite the original file. Otherwise save to a new
    file with `_formatted` appended to the original name.
    """
    resolved_paths = assemble_path_args(*paths)
    final_paths = []

    for path in resolved_paths:
        target_path = None
        dirname, name, item_type, ext = split_filename(path)
        new_name = f"{name}_formatted"
        target_path = join_filename(dirname, new_name, item_type, ext)

        normalize_text_file(path, target_path=target_path)
        if inplace:
            trash(path)
            os.rename(target_path, path)
            print_status("Formatted:\n%s", fmt_lines([fmt_loc(path)]))
            final_paths.append(path)
        else:
            print_status(
                "Formatted:\n%s",
                fmt_lines([f"{fmt_loc(path)} -> {fmt_loc(target_path)}"]),
            )
            final_paths.append(target_path)

    resolvable = resolvable_paths(final_paths)
    if resolvable:
        select(*resolvable)
    return ShellResult(show_selection=len(resolvable) > 0)


@kmd_command
def diff_items(*paths: str, force: bool = False) -> ShellResult:
    """
    Show the unified diff between the given files. It's often helpful to treat diffs
    as items themselves, so this works on items. Items are imported as usual into the
    sandbox workspace if they are not already in the store.

    :param stat: Only show the diffstat summary.
    :param force: If true, will run the diff even if the items are of different formats.
    """
    ws = current_workspace()
    if len(paths) == 2:
        [path1, path2] = paths
    elif len(paths) == 0:
        try:
            last_selections = ws.selections.previous_n(2, expected_size=1)
        except InvalidOperation:
            raise InvalidInput(
                "Need two selections of single files in history or exactly two paths to diff"
            )
        [path1] = last_selections[0].paths
        [path2] = last_selections[1].paths
    else:
        raise InvalidInput("Provide zero paths (to use selections) or two paths to diff")

    [store_path1, store_path2] = import_locator_args(path1, path2)
    item1, item2 = ws.load(store_path1), ws.load(store_path2)

    diff_item = unified_diff_items(item1, item2, strict=not force)
    diff_store_path = ws.save(diff_item, as_tmp=False)
    select(diff_store_path)
    return ShellResult(show_selection=True)


@kmd_command
def diff_files(*paths: str, diffstat: bool = False, save: bool = False) -> ShellResult:
    """
    Show the unified diff between the given files. This works on any files, not
    just items, so helpful for quick analysis without importing the files.

    :param diffstat: Only show the diffstat summary.
    :param save: Save the diff as an item in the store.
    """
    if len(paths) == 2:
        [path1, path2] = paths
    elif len(paths) == 0:
        # If nothing args given, user probably wants diff_items on selections.
        return diff_items()
    else:
        raise InvalidInput("Provide zero paths (to use selections) or two paths to diff")

    path1, path2 = Path(path1), Path(path2)
    diff = unified_diff_files(path1, path2)

    if diffstat:
        cprint(diff.diffstat, text_wrap=Wrap.NONE)
        return ShellResult(show_selection=False)
    else:
        diff_item = Item(
            type=ItemType.doc,
            title=f"Diff of {path1.name} and {path2.name}",
            format=Format.diff,
            body=diff.patch_text,
        )
        ws = current_workspace()
        if save:
            diff_store_path = ws.save(diff_item, as_tmp=False)
            select(diff_store_path)
            return ShellResult(show_selection=True)
        else:
            diff_store_path = ws.save(diff_item, as_tmp=True)
            show(diff_store_path)
            return ShellResult(show_selection=False)
