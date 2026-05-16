from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_OUTPUT_DIR = "project_hygiene_outputs"
EXCLUDED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".pytest_tmp"}
LEGACY_IMPORT_MARKERS = (
    "document_base",
    "parsing",
    "section_detection",
    "extraction",
    "evidence",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    path: str
    message: str


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _iter_dirs(root: Path):
    for path in root.rglob("*"):
        if path.is_dir():
            yield path


def check_git(root: Path) -> dict:
    git_available = False
    is_git_repository = False
    git_status_available = False
    git_status_message = ""

    try:
        subprocess.run(["git", "--version"], cwd=root, capture_output=True, text=True, check=False)
        git_available = True
    except OSError as exc:
        git_status_message = str(exc)

    if git_available:
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        is_git_repository = probe.returncode == 0 and probe.stdout.strip().lower() == "true"
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        git_status_available = status.returncode == 0
        git_status_message = (status.stdout or status.stderr).strip()

    return {
        "git_available": git_available,
        "is_git_repository": is_git_repository,
        "git_status_available": git_status_available,
        "git_status_message": git_status_message,
    }


def scan_test_helpers(root: Path) -> dict:
    helper_files = []
    helper_imports = []
    suspicious_absolute_imports = []

    for path in _iter_files(root):
        rel = _rel(path, root)
        if path.name == "helpers.py" and "tests" in path.parts:
            helper_files.append(rel)
        if path.suffix != ".py" or "tests" not in path.parts:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("from helpers import") or stripped == "import helpers":
                helper_imports.append({"path": rel, "line": line_no, "text": stripped})
            if (
                (stripped.startswith("from ") or stripped.startswith("import "))
                and not stripped.startswith("from .")
                and not stripped.startswith("from __future__")
                and "helpers" in stripped
            ):
                suspicious_absolute_imports.append({"path": rel, "line": line_no, "text": stripped})

    return {
        "helpers_py": sorted(helper_files),
        "from_helpers_imports": helper_imports,
        "suspicious_absolute_imports": suspicious_absolute_imports,
    }


def scan_python_caches(root: Path) -> dict:
    pycache_dirs = []
    pytest_cache_dirs = []
    pytest_tmp_dirs = []
    pyc_files = []

    for path in _iter_dirs(root):
        rel = _rel(path, root)
        if path.name == "__pycache__":
            pycache_dirs.append(rel)
        elif path.name == ".pytest_cache":
            pytest_cache_dirs.append(rel)
        elif path.name == ".pytest_tmp":
            pytest_tmp_dirs.append(rel)

    for path in root.rglob("*.pyc"):
        if path.is_file():
            pyc_files.append(_rel(path, root))

    return {
        "__pycache__": sorted(pycache_dirs),
        ".pytest_cache": sorted(pytest_cache_dirs),
        ".pytest_tmp": sorted(pytest_tmp_dirs),
        "pyc_files": sorted(pyc_files),
        "counts": {
            "__pycache__": len(pycache_dirs),
            ".pytest_cache": len(pytest_cache_dirs),
            ".pytest_tmp": len(pytest_tmp_dirs),
            "pyc_files": len(pyc_files),
        },
    }


def scan_legacy_scripts(root: Path) -> dict:
    scripts = []
    for path in _iter_files(root):
        if path.suffix != ".py":
            continue
        rel = _rel(path, root)
        is_named_legacy = path.name == "run_extraction_test.py"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        marker_hits = [marker for marker in LEGACY_IMPORT_MARKERS if marker in text]
        imports_legacy_chain = len(marker_hits) >= 3
        if is_named_legacy or imports_legacy_chain:
            scripts.append(
                {
                    "path": rel,
                    "is_run_extraction_test": is_named_legacy,
                    "legacy_markers": marker_hits,
                    "imports_legacy_chain": imports_legacy_chain,
                }
            )
    return {"legacy_suspects": scripts}


def scan_requirements(root: Path) -> dict:
    files = []
    unbounded = []
    for path in _iter_files(root):
        if path.name == "requirements.txt" or path.name.startswith("requirements") and path.suffix == ".txt":
            rel = _rel(path, root)
            entries = []
            for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                is_bounded = any(op in line for op in ("==", ">=", "<=", "~=", ">", "<"))
                entry = {"line": line_no, "requirement": line, "is_bounded": is_bounded}
                entries.append(entry)
                if not is_bounded:
                    unbounded.append({"path": rel, **entry})
            files.append({"path": rel, "entries": entries})
    return {"files": sorted(files, key=lambda item: item["path"]), "unbounded_requirements": unbounded}


def scan_retriever_tests(root: Path) -> dict:
    retrievers = []
    for path in sorted(root.glob("*Retriever")):
        if not path.is_dir():
            continue
        tests_dir = path / "tests"
        test_files = sorted(tests_dir.rglob("test_*.py")) if tests_dir.exists() else []
        empty_tests = [test for test in test_files if test.stat().st_size == 0]
        retrievers.append(
            {
                "module": path.name,
                "has_tests_dir": tests_dir.exists(),
                "test_files": [_rel(test, root) for test in test_files],
                "empty_test_files": [_rel(test, root) for test in empty_tests],
                "non_empty_test_count": len(test_files) - len(empty_tests),
            }
        )
    return {"retrievers": retrievers}


def build_findings(report: dict) -> list[Finding]:
    findings: list[Finding] = []
    git = report["git"]
    if not git["is_git_repository"]:
        findings.append(Finding("medium", "git", ".", "Project root is not a Git repository."))
    helpers = report["test_helpers"]
    for item in helpers["from_helpers_imports"]:
        findings.append(
            Finding(
                "high",
                "test_helpers",
                item["path"],
                f"Absolute helper import at line {item['line']}: {item['text']}",
            )
        )
    caches = report["python_caches"]["counts"]
    if any(caches.values()):
        findings.append(Finding("medium", "python_caches", ".", f"Python cache artifacts detected: {caches}"))
    for item in report["legacy_scripts"]["legacy_suspects"]:
        findings.append(Finding("medium", "legacy_scripts", item["path"], "Legacy extraction-chain script suspected."))
    for item in report["requirements"]["unbounded_requirements"]:
        findings.append(
            Finding(
                "medium",
                "requirements",
                item["path"],
                f"Unbounded requirement at line {item['line']}: {item['requirement']}",
            )
        )
    for item in report["retriever_tests"]["retrievers"]:
        if not item["has_tests_dir"] or item["non_empty_test_count"] == 0:
            findings.append(Finding("medium", "retriever_tests", item["module"], "Retriever has no non-empty tests."))
    return findings


def write_reports(report: dict, findings: list[Finding], output_dir: Path, overwrite: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "json": output_dir / "project_hygiene_report.json",
        "jsonl": output_dir / "project_hygiene_findings.jsonl",
        "md": output_dir / "project_hygiene_report.md",
    }
    if not overwrite:
        existing = [str(path) for path in targets.values() if path.exists()]
        if existing:
            raise FileExistsError(f"Report files already exist: {existing}. Use --overwrite.")

    targets["json"].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with targets["jsonl"].open("w", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")

    lines = [
        "# Project Hygiene Audit",
        "",
        f"- Git repository: `{report['git']['is_git_repository']}`",
        f"- Test helpers files: `{len(report['test_helpers']['helpers_py'])}`",
        f"- Absolute helper imports: `{len(report['test_helpers']['from_helpers_imports'])}`",
        f"- Pyc files: `{report['python_caches']['counts']['pyc_files']}`",
        f"- Legacy script suspects: `{len(report['legacy_scripts']['legacy_suspects'])}`",
        f"- Unbounded requirements: `{len(report['requirements']['unbounded_requirements'])}`",
        f"- Retriever modules: `{len(report['retriever_tests']['retrievers'])}`",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for finding in findings:
            lines.append(f"- **{finding.severity}** `{finding.category}` `{finding.path}`: {finding.message}")
    else:
        lines.append("- No findings.")
    targets["md"].write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(project_root: Path, output_dir: Path, overwrite: bool) -> dict:
    root = project_root.resolve()
    report = {
        "project_root": str(root),
        "git": check_git(root),
        "test_helpers": scan_test_helpers(root),
        "python_caches": scan_python_caches(root),
        "legacy_scripts": scan_legacy_scripts(root),
        "requirements": scan_requirements(root),
        "retriever_tests": scan_retriever_tests(root),
    }
    findings = build_findings(report)
    report["summary"] = {
        "findings_count": len(findings),
        "high_findings_count": sum(1 for item in findings if item.severity == "high"),
        "medium_findings_count": sum(1 for item in findings if item.severity == "medium"),
    }
    write_reports(report, findings, output_dir, overwrite)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only project hygiene audit.")
    parser.add_argument("--project-root", default=".", help="Project root to scan.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for audit reports.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_audit(Path(args.project_root), Path(args.output_dir), args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
