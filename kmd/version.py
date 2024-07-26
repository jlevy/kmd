from importlib import metadata
from pathlib import Path
import subprocess
import tomllib


def get_pyproject_version() -> str:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    pyproject_data = tomllib.loads(pyproject_path.read_text())
    return pyproject_data["tool"]["poetry"]["version"]


def get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not read git hash: {e}")
        return "unknown"


def get_version():
    try:
        # For development: use pyproject version + git hash.
        version = get_pyproject_version()
        git_hash = get_git_hash()
        return f"{version}+{git_hash}"
    except Exception:
        # Get the version from the installed package metadata.
        return metadata.version("kmd")


if __name__ == "__main__":
    print(get_version())
