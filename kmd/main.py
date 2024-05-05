import typer
from kmd.actions.action_definitions import fetch_page
from kmd.actions.action_lib import ActionResult
from kmd.actions.registry import load_all_actions
from kmd.media.video import video_download_audio, video_transcription
import kmd.config as config
from kmd.model.model import Item, ItemTypeEnum
from kmd.file_storage.file_store import load_item, save_item

app = typer.Typer()


@app.command()
def download(url: str):
    """
    Download web page or video.
    """

    item = Item(ItemTypeEnum.resource, url=url)
    saved_path = save_item(item)
    print(f"Saved URL to: {saved_path}")

    try:
        # First try as video.
        audio_path = video_download_audio(url)
        print(f"Downloaded video and saved audio to: {audio_path}")
    except ValueError as e:
        # If not a video, download as a web page.
        result = fetch_page([item])
        saved_page = save_item(result[0])
        print(f"Saved page to: {saved_page}")


@app.command()
def transcribe(url: str):
    """
    Download and transcribe video from YouTube or Vimeo
    """

    transcription = video_transcription(url)
    item = Item(ItemTypeEnum.note, body=transcription)
    saved_path = save_item(item)
    print(f"Saved transcription to: {saved_path}")


@app.command()
def action(action_name: str, path: str):
    """
    Perform an action on the given item.
    """

    actions = load_all_actions()
    action = actions[action_name]
    item = load_item(path)
    action_result: ActionResult = action([item])
    for output_item in action_result:
        saved_path = save_item(output_item)
        print(f"Saved output to: {saved_path}")


if __name__ == "__main__":
    config.setup()
    app()
