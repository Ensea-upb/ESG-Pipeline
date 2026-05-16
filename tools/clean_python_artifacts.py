from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".pytest_tmp"}
CACHE_FILE_SUFFIXES = {".pyc", ".pyo"}
PROTECTED_DIR_NAMES = {"outputs", "runs", "ESGFinalCorpus"}
PROTECTED_RELATIVE_DIRS = {
    ("data", "dossier_ingestion_0"),
    ("project_hygiene_outputs",),
}
PROTECTED_SUFFIXES = {".pdf"}


@dataclass
class CleanupItem:
    path: str
    kind: str
    action: str
    status: str
    message: str = ""


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _is_protected(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in PROTECTED_DIR_NAMES for part in rel_parts):
        return path.name not in CACHE_DIR_NAMES and path.suffix.lower() not in CACHE_FILE_SUFFIXES
    return path.suffix.lower() in PROTECTED_SUFFIXES


def find_python_artifacts(root: Path) -> list[tuple[Path, str]]:
    artifacts: list[tuple[Path, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_parts = current.relative_to(root).parts
        if rel_parts in PROTECTED_RELATIVE_DIRS:
            dirnames[:] = []
            continue

        kept_dirnames = []
        for dirname in dirnames:
            child = current / dirname
            child_rel_parts = child.relative_to(root).parts
            if dirname in CACHE_DIR_NAMES:
                artifacts.append((child, "directory"))
                continue
            if dirname in PROTECTED_DIR_NAMES or child_rel_parts in PROTECTED_RELATIVE_DIRS:
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            path = current / filename
            if _is_under_root(path, root) and not _is_protected(path, root) and path.suffix.lower() in CACHE_FILE_SUFFIXES:
                artifacts.append((path, "file"))
    # Delete deepest directories first when executing.
    return sorted(artifacts, key=lambda item: (len(item[0].parts), item[0].as_posix()), reverse=True)


def clean_artifacts(project_root: Path, execute: bool) -> list[CleanupItem]:
    root = project_root.resolve()
    items: list[CleanupItem] = []
    for path, kind in find_python_artifacts(root):
        rel = _rel(path, root)
        if not execute:
            items.append(CleanupItem(rel, kind, "would_delete", "ok"))
            continue
        try:
            if kind == "directory":
                shutil.rmtree(path)
            else:
                path.unlink()
            items.append(CleanupItem(rel, kind, "deleted", "ok"))
        except PermissionError as exc:
            items.append(CleanupItem(rel, kind, "delete", "permission_error", str(exc)))
        except FileNotFoundError:
            items.append(CleanupItem(rel, kind, "delete", "already_missing"))
        except OSError as exc:
            items.append(CleanupItem(rel, kind, "delete", "error", str(exc)))
    return items


def write_reports(items: list[CleanupItem], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": len(items),
        "ok": sum(1 for item in items if item.status == "ok"),
        "permission_errors": sum(1 for item in items if item.status == "permission_error"),
        "errors": sum(1 for item in items if item.status == "error"),
        "items": [asdict(item) for item in items],
    }
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = report_path.with_suffix(".md")
    lines = [
        "# Python Artifacts Cleanup Report",
        "",
        f"- Total candidates: `{summary['total']}`",
        f"- OK: `{summary['ok']}`",
        f"- Permission errors: `{summary['permission_errors']}`",
        f"- Other errors: `{summary['errors']}`",
        "",
        "## Items",
        "",
    ]
    for item in items[:200]:
        lines.append(f"- `{item.action}` `{item.kind}` `{item.path}`: {item.status} {item.message}".rstrip())
    if len(items) > 200:
        lines.append(f"- ... {len(items) - 200} more item(s)")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely clean Python cache artifacts.")
    parser.add_argument("--project-root", default=".", help="Project root to clean.")
    parser.add_argument("--report-path", default="python_artifacts_cleanup_report.json", help="JSON report path.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="List candidates without deleting them.")
    mode.add_argument("--execute", action="store_true", help="Actually delete Python cache artifacts.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    execute = bool(args.execute)
    items = clean_artifacts(Path(args.project_root), execute=execute)
    write_reports(items, Path(args.report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
