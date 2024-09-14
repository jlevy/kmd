import subprocess
from rich import print as rprint


def _run(cmd: list[str]) -> int:
    rprint(f"[bold green]❯ {' '.join(cmd)}[/bold green]")
    errcount = 0
    try:
        subprocess.run(cmd, text=True, check=True)
    except subprocess.CalledProcessError as e:
        rprint(f"[bold red]Error: {e}[/bold red]")
        errcount = 1
    rprint()

    return errcount


def main():
    rprint()

    errcount = 0
    errcount += _run(["usort", "format", "kmd", "tests"])
    errcount += _run(["ruff", "check", "--fix", "kmd", "tests"])
    errcount += _run(["black", "kmd", "tests"])

    rprint()

    if errcount != 0:
        rprint(f"[bold red]✗ Lint failed with {errcount} errors.[/bold red]")
    else:
        rprint("[bold green]✔️ Lint passed![/bold green]")
    rprint()

    return errcount


if __name__ == "__main__":
    exit(main())
