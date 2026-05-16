from __future__ import annotations

from pathlib import Path
from typing import Any

from .dataset_builder import build_dataset


def build_multi_company_year_dataset(input_root: Path, output_dir: Path, overwrite: bool = False) -> dict[str, Any]:
    return build_dataset(input_root=input_root, output_dir=output_dir, overwrite=overwrite)
