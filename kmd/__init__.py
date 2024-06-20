import os
from pathlib import Path
from typing import List


kmd_base_path = Path(os.path.dirname(__file__))


def _assemble_source_code(module_path: Path) -> str:
    source_files = [f for f in os.listdir(module_path) if f.endswith(".py") and f != "__init__.py"]
    output: List[str] = []

    for filename in source_files:
        with open(module_path / filename, "r") as file:
            file_content: str = file.read()
        header = f"\n\n# {filename}:)\n\n"
        footer = f"\n\n"

        output.append(header + file_content + footer)

    return "".join(output)


model_sources_str: str = _assemble_source_code(kmd_base_path / "model")
