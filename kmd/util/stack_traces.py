import signal
import sys
import threading
import traceback
from cachetools import cached


def dump_stack_traces(signum, frame):
    """
    Print stack traces for all threads to stderr.
    """

    print(f"\n\nReceived signal {signum}, will dump stack traces:\n", file=sys.stderr)

    main_thread_id = threading.get_ident()
    print(
        f"Thread ID: {main_thread_id} (Main Thread)\n",
        "".join(traceback.format_stack(frame)),
        file=sys.stderr,
    )

    for thread_id, stack_frame in sys._current_frames().items():
        if thread_id == main_thread_id:
            continue  # Already printed.
        print(f"\nThread ID: {thread_id}", file=sys.stderr)
        print("".join(traceback.format_stack(stack_frame)), file=sys.stderr)


@cached(cache={})
def add_stacktrace_handler(sig=signal.SIGUSR1):
    """To use: `pkill -USR1 -f 'module_name'"""

    signal.signal(sig, dump_stack_traces)
