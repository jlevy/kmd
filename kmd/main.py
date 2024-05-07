import typer
from kmd.actions.action_definitions import fetch_page
from kmd.actions.action_lib import ActionResult
from kmd.actions.registry import load_all_actions
from kmd.media.url import canonicalize_url
from kmd.media.video import video_download_audio, video_transcription
import kmd.config as config
from kmd.model.model import Format, Item, ItemType
from kmd.file_storage.file_store import workspace

app = typer.Typer()


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


if __name__ == "__main__":
    config.setup()
    app()
