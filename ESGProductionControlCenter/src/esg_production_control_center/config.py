from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ControlCenterConfig:
    project_root: Path
    control_root: Path
    runs_dir: Path
    outputs_dir: Path


def get_config(project_root: str | Path = ".") -> ControlCenterConfig:
    root = Path(project_root).resolve()
    control_root = root / "ESGProductionControlCenter"
    return ControlCenterConfig(
        project_root=root,
        control_root=control_root,
        runs_dir=control_root / "runs",
        outputs_dir=control_root / "outputs",
    )


def ensure_control_dirs(config: ControlCenterConfig) -> None:
    config.runs_dir.mkdir(parents=True, exist_ok=True)
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
