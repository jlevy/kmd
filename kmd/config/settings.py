from pathlib import Path

from cachetools import cached


APP_NAME = "kmd"


@cached(cache={})
def media_cache_dir():
    """
    The media cache directory. Set at load time and used for the entire session.
    """
    return f"{Path(".").absolute()}/cache/media"
