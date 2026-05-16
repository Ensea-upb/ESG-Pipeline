from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .module_registry import get_module_registry


def assert_safe_project_path(path: str | Path, project_root: str | Path = ".") -> Path:
    root = Path(project_root).resolve()
    resolved = Path(path).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Path is outside project root: {path}")
    if ".." in Path(path).parts:
        raise ValueError(f"Parent traversal is not allowed: {path}")
    return resolved


def build_run_command(module_name: str, input_dir: str | Path, output_dir: str | Path, project_root: str | Path = ".", overwrite: bool = False, dry_run: bool = True, reuse_existing: bool = False, force_rerun: bool = False) -> dict[str, Any]:
    registry = get_module_registry()
    if module_name not in registry:
        raise KeyError(f"Unknown module: {module_name}")
    spec = registry[module_name]
    safe_input = assert_safe_project_path(input_dir, project_root)
    safe_output = assert_safe_project_path(output_dir, project_root)
    command = [sys.executable, spec.run_script, "--input-dir", str(safe_input), "--output-dir", str(safe_output)]
    if overwrite:
        command.append("--overwrite")
    if module_name == "ESGExtractionOrchestrator":
        if reuse_existing:
            command.append("--reuse-existing")
        if force_rerun:
            command.append("--force-rerun")
    return {
        "module_name": module_name,
        "input_dir": str(safe_input),
        "output_dir": str(safe_output),
        "command": command,
        "dry_run": bool(dry_run),
        "overwrite": bool(overwrite),
        "reuse_existing": bool(reuse_existing),
        "force_rerun": bool(force_rerun),
    }


def build_validation_command(module_name: str, output_dir: str | Path, project_root: str | Path = ".") -> dict[str, Any]:
    registry = get_module_registry()
    spec = registry[module_name]
    safe_output = assert_safe_project_path(output_dir, project_root)
    command = [sys.executable, spec.validation_script, "--output-dir", str(safe_output), "--contract-path", spec.contract_path]
    return {"module_name": module_name, "output_dir": str(safe_output), "contract_path": spec.contract_path, "command": command}
