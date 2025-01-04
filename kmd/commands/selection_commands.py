from kmd.commands.command_registry import kmd_command
from kmd.config.logger import get_logger
from kmd.errors import InvalidInput
from kmd.lang_tools.inflection import plural
from kmd.model.paths_model import StorePath
from kmd.model.shell_model import ShellResult
from kmd.shell_ui.shell_output import print_status
from kmd.shell_ui.shell_results import shell_print_selection_history
from kmd.workspaces.selections import Selection
from kmd.workspaces.workspaces import current_workspace

log = get_logger(__name__)


@kmd_command
def select(
    *paths: str,
    history: bool = False,
    last: int = 0,
    back: int = 0,
    forward: int = 0,
    previous: bool = False,
    next: bool = False,
    pop: bool = False,
    clear: bool = False,
    clear_future: bool = False,
) -> ShellResult:
    """
    Set or show the current selection.

    If no arguments are given, show the current selection.

    If paths are given, the new selection is pushed to the selection history.

    If any other flags are given, they show or modify the selection history.
    They must be used individually (and without paths).

    :param history: Show the full selection history.
    :param last: Show the last `last` selections in the history.
    :param back: Move back in the selection history by `back` steps.
    :param forward: Move forward in the selection history by `forward` steps.
    :param previous: Move back in the selection history to the previous selection.
    :param next: Move forward in the selection history to the next selection.
    :param pop: Pop the current selection from the history.
    :param clear: Clear the full selection history.
    :param clear_future: Clear all selections from history after the current one.
    """
    ws = current_workspace()

    # TODO: It would be nice to be able to read stdin from a pipe but this isn't working rn.
    # You could then run `... | select --stdin` to select the piped input.
    # Globally we have THREAD_SUBPROCS=False to avoid hard-to-interrupt subprocesses.
    # But xonsh seems to hang with stdin unless we modify the spec to be threadable?
    # https://xon.sh/tutorial.html#callable-aliases
    # https://github.com/xonsh/xonsh/blob/main/xonsh/aliases.py#L1070
    # if stdin:
    #     paths = tuple(sys.stdin.read().splitlines())

    exclusive_flags = [history, last, back, forward, previous, next, pop, clear, clear_future]
    if sum(bool(f) for f in exclusive_flags) > 1:
        raise InvalidInput("Cannot combine multiple flags")
    if paths and any(exclusive_flags):
        raise InvalidInput("Cannot combine paths with other flags")

    if paths:
        store_paths = [StorePath(path) for path in paths]
        ws.selections.push(Selection(paths=store_paths))
        return ShellResult(show_selection=False)
    elif history:
        shell_print_selection_history(ws.selections)
        return ShellResult(show_selection=False)
    elif last:
        shell_print_selection_history(ws.selections, last=last)
        return ShellResult(show_selection=False)
    elif back:
        ws.selections.previous(back)
        return ShellResult(show_selection=True)
    elif forward:
        ws.selections.next(forward)
        return ShellResult(show_selection=True)
    elif previous:
        ws.selections.previous()
        return ShellResult(show_selection=True)
    elif next:
        ws.selections.next()
        return ShellResult(show_selection=True)
    elif pop:
        ws.selections.pop()
        return ShellResult(show_selection=True)
    elif clear:
        ws.selections.clear()
        return ShellResult(show_selection=True)
    elif clear_future:
        ws.selections.clear_future()
        return ShellResult(show_selection=True)
    else:
        return ShellResult(show_selection=True)


@kmd_command
def unselect(*paths: str) -> ShellResult:
    """
    Remove items from the current selection. Handy if you've just selected some items and
    wish to unselect a few of them. Used without arguments, makes the current selection empty.
    """
    ws = current_workspace()

    current_paths = ws.selections.current.paths.copy()
    new_paths = ws.selections.unselect_current([StorePath(path) for path in paths]).paths

    n_removed = len(current_paths) - len(new_paths)
    print_status(
        "Unselected %s %s, %s now selected.",
        n_removed,
        plural("item", n_removed),
        len(new_paths),
    )

    return ShellResult(show_selection=True)


@kmd_command
def selections(
    last: int = 3,
    clear: bool = False,
    clear_future: bool = False,
) -> ShellResult:
    """
    Show the recent selection history. Same as `select --last=3` by default.
    """
    exclusive_flags = [clear, clear_future]
    exclusive_flag_count = sum(bool(f) for f in exclusive_flags)
    if exclusive_flag_count > 1:
        raise InvalidInput("Cannot combine multiple flags")
    if exclusive_flag_count:
        last = 0
    return select(last=last, clear=clear, clear_future=clear_future)


@kmd_command
def prev_selection() -> ShellResult:
    """
    Move back in the selection history to the previous selection.
    Same as `select --previous`.
    """
    return select(previous=True)


@kmd_command
def next_selection() -> ShellResult:
    """
    Move forward in the selection history to the next selection.
    Same as `select --next`.
    """
    return select(next=True)
