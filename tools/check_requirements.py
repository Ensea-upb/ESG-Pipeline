from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".pytest_tmp", "outputs", "runs"}
NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
BOUNDS_RE = re.compile(r"(==|~=|>=|<=|>|<)")


def iter_requirement_files(root: Path):
    for path in root.rglob("requirements*.txt"):
        parts = set(path.relative_to(root).parts)
        if parts & EXCLUDED_PARTS:
            continue
        if "data" in parts:
            continue
        yield path


def normalize_name(requirement: str) -> str:
    match = NAME_RE.match(requirement)
    return match.group(1).lower().replace("_", "-") if match else requirement.lower()


def check_requirements(root: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[tuple[str, str], str] = {}
    for path in iter_requirement_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            errors.append(f"{rel}: cannot read file: {exc}")
            continue
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            if not BOUNDS_RE.search(line):
                errors.append(f"{rel}:{line_no}: unbounded requirement `{line}`")
            name = normalize_name(line)
            key = (rel, name)
            previous = seen.get(key)
            if previous and previous != line:
                errors.append(f"{rel}:{line_no}: duplicate contradictory requirement `{line}` vs `{previous}`")
            seen[key] = line
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate project requirements files.")
    parser.add_argument("--project-root", default=".", help="Project root to scan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = check_requirements(Path(args.project_root).resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("OK: requirements files are bounded and readable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
