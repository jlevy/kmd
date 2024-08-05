import hashlib
import os
from pathlib import Path


def hash_file(file_path: str | Path, algorithm: str = "sha1") -> str:
    """
    Hash the content of a file using the specified algorithm and return a string in the
    format `algorithm:hash`.
    """
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)
    file_path = Path(file_path)

    with file_path.open("rb") as file:
        while chunk := file.read(8192):
            hasher.update(chunk)

    return f"{algorithm}:{hasher.hexdigest()}"


## Tests


def test_hash_file():
    os.makedirs("tmp", exist_ok=True)
    file_path = "tmp/test_file.txt"

    with open(file_path, "w") as f:
        f.write("Hello, World!")

    result_hash = hash_file(file_path, "sha1")
    assert result_hash == "sha1:0a0a9f2a6772942557ab5355d76af442f8f65e01"
