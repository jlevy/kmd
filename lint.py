import subprocess
from rich import print as rprint


def _run(cmd: list[str]):
    rprint(f"[bold green]{' '.join(cmd)}[/bold green]")
    subprocess.run(cmd, check=True)
    rprint()


def main():
    _run(["ruff", "check", "--fix", "kmd", "tests"])
    _run(["black", "kmd", "tests"])


if __name__ == "__main__":
    main()
