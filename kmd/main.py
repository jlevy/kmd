import typer

from kmd.media.video import video_download, video_transcription
import kmd.config as config

app = typer.Typer()


@app.command()
def download(url: str):
    """Download video from YouTube or Vimeo. Saves results in cache."""

    audio_path = video_download(url)
    print(f"Downloaded audio to: {audio_path}")


@app.command()
def transcribe(url: str):
    """Download video from YouTube or Vimeo and transcribe it. Saves results in cache."""

    transcription = video_transcription(url)
    print(f"Transcription:\n\n{transcription}")


if __name__ == "__main__":
    config.setup()
    app()
