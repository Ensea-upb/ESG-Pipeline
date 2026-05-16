from __future__ import annotations

import argparse
import sys
from pathlib import Path


EXCLUDED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".pytest_tmp"}


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_python_tests(root: Path):
    for path in root.rglob("tests"):
        if not path.is_dir():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        yield path


def check_project(project_root: Path) -> list[str]:
    root = project_root.resolve()
    errors: list[str] = []

    for tests_dir in _iter_python_tests(root):
        helper = tests_dir / "helpers.py"
        if helper.exists() and not (tests_dir / "__init__.py").exists():
            errors.append(f"{_rel(tests_dir, root)} has helpers.py but no __init__.py")

        for path in tests_dir.rglob("*.py"):
            if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as exc:
                errors.append(f"{_rel(path, root)} could not be read: {exc}")
                continue
            for line_no, line in enumerate(lines, start=1):
                stripped = line.strip()
                if stripped.startswith("from helpers import") or stripped == "import helpers":
                    errors.append(f"{_rel(path, root)}:{line_no} uses absolute helpers import")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check test helper imports are package-relative.")
    parser.add_argument("--project-root", default=".", help="Project root to scan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = check_project(Path(args.project_root))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("OK: no absolute test helpers imports found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
