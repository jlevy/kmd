import typer
from kmd.actions.registry import load_all_actions
from kmd.media.video import video_download, video_transcription
import kmd.config as config
from kmd.model.items import Item, ItemTypeEnum
from kmd.workspace.file_store import load_item, save_item

app = typer.Typer()


@app.command()
def download(url: str):
    """
    Download video from YouTube or Vimeo.
    """

    audio_path = video_download(url)
    print(f"Downloaded audio to: {audio_path}")


@app.command()
def transcribe(url: str):
    """
    Download video from YouTube or Vimeo and transcribe it.
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
    output_item = action([item])
    saved_path = save_item(output_item)
    print(f"Saved output to: {saved_path}")


if __name__ == "__main__":
    config.setup()
    app()
