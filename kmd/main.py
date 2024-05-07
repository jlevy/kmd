"""
kmd: A command line for knowledge exploration.
"""

import logging
import sys
from typer import Typer

import kmd.config as config
from kmd.config import APP_NAME
from kmd.tui import tui
from kmd.actions.action_definitions import fetch_page
from kmd.actions.action_lib import ActionResult
from kmd.actions.registry import load_all_actions
from kmd.media.url import canonicalize_url
from kmd.media.video import video_download_audio, video_transcription
from kmd.model.model import Format, Item, ItemType
from kmd.file_storage.file_store import workspace

app = Typer(help=__doc__)


# TODO: Make download and transcribe true actions. Need to chain them off a url item.


@app.command()
def download(url: str):
    """
    Download web page or video.
    """

    url = canonicalize_url(url)
    item = Item(ItemType.resource, url=url, format=Format.url)
    saved_url = workspace.save(item)
    print(f"Saved URL to: {saved_url}")

    try:
        # First try as video.
        audio_path = video_download_audio(url)
        print(f"Downloaded video and saved audio to: {audio_path}")
    except ValueError as e:
        # If not a video, download as a web page.
        result = fetch_page([item])
        saved_page = workspace.save(result[0])
        print(f"Saved page to: {saved_page}")


@app.command()
def transcribe(url: str):
    """
    Download and transcribe video from YouTube or Vimeo
    """

    url = canonicalize_url(url)
    download(url)
    transcription = video_transcription(url)
    item = Item(ItemType.note, body=transcription, format=Format.plaintext)
    saved_path = workspace.save(item)
    print(f"Saved transcription to: {saved_path}")


@app.command()
def action(action_name: str, path: str):
    """
    Perform an action on the given item.
    """

    actions = load_all_actions()
    action = actions[action_name]
    item = workspace.load(path)
    action_result: ActionResult = action([item])
    for output_item in action_result:
        saved_path = workspace.save(output_item)
        print(f"Saved output to: {saved_path}")


@app.command()
def ui():
    """
    Run the text-based user interface.
    """
    tui.run()


if __name__ == "__main__" or __name__.endswith(".main"):
    config.setup()

    log = logging.getLogger(__name__)
    log.info("%s invoked: %s", APP_NAME, " ".join(sys.argv))

    if len(sys.argv) == 1:
        app(prog_name=APP_NAME, args=["--help"])
    else:
        app()
