from __future__ import annotations

from pathlib import Path

from .io_utils import read_csv


def load_consolidated_candidates(input_dir: Path) -> tuple[Path, list[dict[str, str]]]:
    path = input_dir / "consolidated_unique_candidates.csv"
    if not path.exists():
        path = input_dir / "consolidated_candidates.csv"
    return path, read_csv(path)
