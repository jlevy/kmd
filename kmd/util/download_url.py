import contextlib
import logging
from urllib.parse import urlparse

import requests
from strif import atomic_output_file, copyfile_atomic

log = logging.getLogger(__name__)

# Some sites block python user agent.
USER_AGENT_MOZILLA_MAC = "Mozilla/5.0 (Compatible, Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"


def user_agent_headers(agent=USER_AGENT_MOZILLA_MAC):
    return {"User-Agent": agent}


def download_url(
    url,
    target_filename,
    session=None,
    silent=False,
    timeout=30,
    auth=None,
    headers=None,
):
    """Download given file, optionally with progress bar.

    Output file is created atomically. Content stored as binary, without
    any character decoding.
    """
    parsed_url = urlparse(url)
    if not silent:
        log.info("%s", url)

    if parsed_url.scheme == "file" or parsed_url.scheme == "":
        copyfile_atomic(parsed_url.netloc + parsed_url.path, target_filename)
    elif parsed_url.scheme == "s3":
        import boto3  # type: ignore

        s3 = boto3.resource("s3")
        s3.Bucket(parsed_url.netloc).download_file(parsed_url.path[1:], target_filename)
    else:
        do_get = session.get if session else requests.get
        with contextlib.closing(
            do_get(
                url,
                stream=True,
                timeout=timeout,
                auth=auth,
                headers=headers or user_agent_headers(),
            )
        ) as response:
            total_size = int(response.headers.get("content-length", 0))
            response.raise_for_status()
            with atomic_output_file(target_filename, make_parents=True) as target_filename:
                with open(target_filename, "wb") as f:
                    if silent:
                        for data in response.iter_content(None):
                            f.write(data)
                    else:
                        # WARN: Importing tqdm here to avoid a circular dependency
                        from tqdm import tqdm

                        with tqdm(total=total_size, unit="B", unit_scale=True) as progress:
                            for data in response.iter_content(None):
                                progress.update(len(data))
                                f.write(data)
