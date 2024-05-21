from pathlib import Path

from cachetools import cached


APP_NAME = "kmd"


# FIXME: Rename cache to kmd_cache and walk up dir heirarchy to find cache dir.
@cached(cache={})
def media_cache_dir():
    """
    The media cache directory. Set at load time and used for the entire session.
    """
    return f"{Path(".").absolute()}/cache/media"
