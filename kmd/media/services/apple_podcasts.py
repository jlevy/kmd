from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import date
from yt_dlp.utils import DownloadError
from kmd.file_formats.yaml_util import to_yaml_string
from kmd.media.yt_dlp_utils import ydl_download_audio, ydl_extract_info
from kmd.config.text_styles import EMOJI_WARN
from kmd.model.errors_model import ApiResultError
from kmd.util.type_utils import not_none
from kmd.util.url import Url
from kmd.model.media_model import SERVICE_APPLE_PODCASTS, MediaMetadata, MediaService, MediaUrlType
from kmd.config.logger import get_logger

log = get_logger(__name__)


# URL format is podcast id and episode id:
# https://podcasts.apple.com/us/podcast/upper-priest-lake-trail-to-continental-creek-trail/id1303792223?i=1000394194840
# which is equivalent to
# https://podcasts.apple.com/podcast/id1303792223?i=1000394194840
# See:
# https://podcasters.apple.com/support/847-hosts-and-guests


class ApplePodcasts(MediaService):
    def get_media_id(self, url: Url) -> Optional[str]:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ("podcasts.apple.com", "itunes.apple.com"):
            path_parts = parsed_url.path.split("/")
            for part in path_parts:
                if part.startswith("id"):
                    podcast_id = part
                    query = parse_qs(parsed_url.query)
                    episode_id = query.get("i", [None])[0]
                    if episode_id:
                        return f"{podcast_id}?i={episode_id}"
        return None

    def canonicalize_and_type(self, url: Url) -> Tuple[Optional[Url], Optional[MediaUrlType]]:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ("podcasts.apple.com", "itunes.apple.com"):
            path_parts = parsed_url.path.split("/")
            for part in path_parts:
                if part.startswith("id"):
                    podcast_id = part
                    query = parse_qs(parsed_url.query)
                    episode_id = query.get("i", [None])[0]
                    if episode_id:
                        return (
                            Url(f"https://podcasts.apple.com/podcast/{podcast_id}?i={episode_id}"),
                            MediaUrlType.episode,
                        )
                    return (
                        Url(f"https://podcasts.apple.com/podcast/{podcast_id}"),
                        MediaUrlType.podcast,
                    )
        return None, None

    def thumbnail_url(self, url: Url) -> Optional[Url]:
        # Apple Podcasts doesn't have a standardized thumbnail URL format.
        # We'll need to extract this from the metadata.
        try:
            metadata = self.metadata(url)
            return metadata.thumbnail_url if metadata else None
        except DownloadError as e:
            log.warning("Could not get a thumbnail URL; will skip: %s", e)
            return None

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        # Apple Podcasts doesn't support timestamp links. We'll return the original URL.
        return url

    def download_audio(self, url: Url, target_dir: Path) -> Path:
        url = not_none(self.canonicalize(url), "Not a recognized Apple Podcasts URL")
        return ydl_download_audio(url, target_dir)

    def _extract_info(self, url: Url) -> Dict[str, Any]:
        url = not_none(self.canonicalize(url), "Not a recognized Apple Podcasts URL")
        return ydl_extract_info(url)

    def metadata(self, url: Url, full: bool = False) -> MediaMetadata:
        url = not_none(self.canonicalize(url), "Not a recognized Apple Podcasts URL")
        yt_result: Dict[str, Any] = self._extract_info(url)

        return self._parse_metadata(yt_result, full=full)

    def list_channel_items(self, url: Url) -> List[MediaMetadata]:
        result = self._extract_info(url)

        if "entries" in result:
            entries = result["entries"]
        else:
            log.warning("%s No episodes found in the podcast.", EMOJI_WARN)
            entries = []

        episode_meta_list: List[MediaMetadata] = []

        for entry in entries:
            episode_meta_list.append(self._parse_metadata(entry))

        log.message("Found %d episodes in podcast %s", len(episode_meta_list), url)

        return episode_meta_list

    def _parse_metadata(
        self, yt_result: Dict[str, Any], full: bool = False, **overrides: Dict[str, Any]
    ) -> MediaMetadata:
        try:
            media_id = yt_result["id"]
            if not media_id:
                raise KeyError("No ID found")

            url = yt_result.get("webpage_url") or yt_result.get("url")
            if not url:
                raise KeyError("No URL found")

            thumbnail_url = yt_result.get("thumbnail")

            upload_date_str = yt_result.get("upload_date")
            upload_date = date.fromisoformat(upload_date_str) if upload_date_str else None

            result = MediaMetadata(
                media_id=media_id,
                media_service=SERVICE_APPLE_PODCASTS,
                url=url,
                thumbnail_url=thumbnail_url,
                title=yt_result["title"],
                description=yt_result.get("description"),
                upload_date=upload_date,
                channel_url=Url(yt_result.get("channel_url", "")),
                view_count=yt_result.get("view_count"),
                duration=yt_result.get("duration"),
                heatmap=None,
                **overrides,
            )
            log.message("Parsed Apple Podcasts metadata: %s", result)
        except KeyError as e:
            log.error("Missing key in Apple Podcasts metadata (see saved object): %s", e)
            log.save_object(
                "yt_dlp result", None, to_yaml_string(yt_result, stringify_unknown=True)
            )
            raise ApiResultError("Did not find key in Apple Podcasts metadata: %s" % e)

        return result


## Tests


def test_canonicalize_apple():
    apple = ApplePodcasts()

    assert apple.get_media_id(Url("https://podcasts.apple.com/us/podcast/id1627920305")) is None
    assert apple.get_media_id(Url("https://podcasts.apple.com/podcast/id1234567890")) is None
    assert apple.get_media_id(Url("https://example.com/podcast/123")) is None

    assert (
        apple.get_media_id(Url("https://podcasts.apple.com/podcast/id1234567890?i=1000635337486"))
        == "id1234567890?i=1000635337486"
    )

    def assert_canon(url: str, canon_url: str):
        assert apple.canonicalize(Url(url)) == Url(canon_url)

    assert_canon(
        "https://podcasts.apple.com/us/podcast/redefining-success-money-and-belonging-paul-millerd/id1627920305?i=1000635337486",
        "https://podcasts.apple.com/podcast/id1627920305?i=1000635337486",
    )

    assert_canon(
        "https://podcasts.apple.com/us/podcast/redefining-success-money-and-belonging-paul-millerd/id1627920305?i=1000635337486",
        "https://podcasts.apple.com/podcast/id1627920305?i=1000635337486",
    )
