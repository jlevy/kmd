import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import cast, Optional
from urllib.request import Request, urlopen
from zipfile import ZipFile

from tldr import (
    DOWNLOAD_CACHE_LOCATION,
    get_cache_dir,
    get_language_list,
    get_page,
    REQUEST_HEADERS,
    store_page_to_cache,
    URLOPEN_CONTEXT,
)

from kmd.config.logger import get_logger

log = get_logger(__name__)


CACHE_UPDATE_INTERVAL = timedelta(days=14)

_cache_dir = Path(get_cache_dir())
_timestamp_file = _cache_dir / ".tldr_cache_timestamp"


def _should_update_cache() -> bool:
    try:
        if not _timestamp_file.exists():
            return True
        last_update = datetime.fromtimestamp(_timestamp_file.stat().st_mtime)
        return last_update < datetime.now() - CACHE_UPDATE_INTERVAL
    except Exception:
        return True


# Copied from tldr.py with adjustments.
def _update_cache() -> None:
    languages = get_language_list()
    for language in languages:
        try:
            cache_location = f"{DOWNLOAD_CACHE_LOCATION[:-4]}-pages.{language}.zip"
            log.warning(
                f"Updating tldr cache for language {language}: {cache_location} -> {_cache_dir}"
            )
            req = urlopen(Request(cache_location, headers=REQUEST_HEADERS), context=URLOPEN_CONTEXT)
            zipfile = ZipFile(BytesIO(req.read()))
            pattern = re.compile(r"(.+)/(.+)\.md")
            cached = 0
            for entry in zipfile.namelist():
                match = pattern.match(entry)
                if match:
                    bytestring = zipfile.read(entry)
                    store_page_to_cache(
                        bytestring,  # type: ignore (tldr seems to have wrong type)
                        match.group(2),
                        match.group(1),
                        language,
                    )
                    cached += 1

        except Exception as e:
            log.error(
                f"Error: Unable to update tldr cache for language {language} from {cache_location}: {e}"
            )

    _timestamp_file.parent.mkdir(parents=True, exist_ok=True)
    _timestamp_file.touch()


def tldr_refresh_cache() -> bool:
    """Refresh the full TLDR cache."""
    if _should_update_cache():
        _update_cache()
        return True
    return False


def tldr_help(text: str) -> Optional[str]:
    """
    Get TLDR help for a command. Pre-caches all pages with occasional refresh.
    """

    tldr_refresh_cache()

    page_data = cast(Optional[list[bytes]], get_page(text))
    if not page_data:
        return None
    assert isinstance(page_data, list) and all(isinstance(item, bytes) for item in page_data)
    page_str = "\n".join(data.decode("utf-8") for data in page_data)

    return page_str
