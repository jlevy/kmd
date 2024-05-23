import threading


def synchronized(func):
    """
    Convenience decorator to ensure a function is executed by only one thread at a time.
    """
    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func
