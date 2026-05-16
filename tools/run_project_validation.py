from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


CORE_MODULES = [
    "ESGInformationExtraction",
    "ESGCSVExtraction",
    "ESGVisualExtraction",
    "ESGTableExtraction",
    "ESGExtractionOrchestrator",
    "ESGIndicatorValidation",
    "ESGManualReview",
    "ESGIndicatorDatabase",
    "ESGProductionControlCenter",
]


@dataclass
class ValidationStep:
    name: str
    command: list[str]
    returncode: int
    status: str
    stdout_tail: str
    stderr_tail: str


Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


def default_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def run_step(name: str, command: list[str], root: Path, runner: Runner = default_runner) -> ValidationStep:
    result = runner(command, root)
    return ValidationStep(
        name=name,
        command=command,
        returncode=result.returncode,
        status="passed" if result.returncode == 0 else "failed",
        stdout_tail=tail(result.stdout or ""),
        stderr_tail=tail(result.stderr or ""),
    )


def build_commands(root: Path, full: bool, skip_retrievers: bool, basetemp_root: Path | None = None) -> list[tuple[str, list[str]]]:
    py = sys.executable
    if basetemp_root is None:
        basetemp_root = Path(tempfile.mkdtemp(prefix="esg_pytest_validation_"))
    commands: list[tuple[str, list[str]]] = [
        ("check_test_helper_imports", [py, "tools/check_test_helper_imports.py", "--project-root", "."]),
        ("check_requirements", [py, "tools/check_requirements.py", "--project-root", "."]),
        (
            "compileall_core_modules",
            [py, "-m", "compileall", "-q", *CORE_MODULES],
        ),
    ]
    if full:
        for module in CORE_MODULES:
            bt = str(basetemp_root / f"validation_{module}")
            commands.append((f"pytest_{module}", [py, "-m", "pytest", f"{module}/tests", "--basetemp", bt]))
        if not skip_retrievers:
            bt = str(basetemp_root / "validation_retrievers")
            commands.append(
                (
                    "pytest_retrievers",
                    [py, "-m", "pytest", "AnnualReportRetriever/tests", "--basetemp", bt],
                )
            )
        bt_global = str(basetemp_root / "validation_global")
        commands.append(("pytest_global", [py, "-m", "pytest", "--basetemp", bt_global]))
    else:
        bt_quick = str(basetemp_root / "validation_quick")
        commands.append(
            (
                "pytest_project_hygiene",
                [py, "-m", "pytest", "tests/project_hygiene", "--basetemp", bt_quick],
            )
        )
    return commands


def write_reports(steps: list[ValidationStep], json_report: Path, markdown_report: Path) -> None:
    json_report.parent.mkdir(parents=True, exist_ok=True)
    markdown_report.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if all(step.returncode == 0 for step in steps) else "failed"
    payload = {
        "status": status,
        "steps_total": len(steps),
        "steps_passed": sum(1 for step in steps if step.returncode == 0),
        "steps_failed": sum(1 for step in steps if step.returncode != 0),
        "steps": [asdict(step) for step in steps],
    }
    json_report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Project Validation Report",
        "",
        f"- Status: `{status}`",
        f"- Steps: `{payload['steps_passed']}/{payload['steps_total']}` passed",
        "",
        "## Steps",
        "",
    ]
    for step in steps:
        command = " ".join(step.command)
        lines.append(f"- **{step.status}** `{step.name}`: `{command}`")
        if step.returncode != 0 and step.stderr_tail:
            lines.append("")
            lines.append("```text")
            lines.append(step.stderr_tail)
            lines.append("```")
            lines.append("")
    markdown_report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation(
    project_root: Path,
    full: bool,
    skip_retrievers: bool,
    json_report: Path,
    markdown_report: Path,
    runner: Runner = default_runner,
    basetemp_root: Path | None = None,
) -> list[ValidationStep]:
    root = project_root.resolve()
    steps = [run_step(name, command, root, runner=runner) for name, command in build_commands(root, full, skip_retrievers, basetemp_root=basetemp_root)]
    write_reports(steps, json_report, markdown_report)
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run project hygiene validation.")
    parser.add_argument("--project-root", default=".", help="Project root.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run quick hygiene checks.")
    mode.add_argument("--full", action="store_true", help="Run full module and global pytest validation.")
    parser.add_argument("--skip-retrievers", action="store_true", help="Skip retriever tests in full mode.")
    parser.add_argument("--json-report", default="project_validation_summary.json", help="JSON report path.")
    parser.add_argument("--markdown-report", default="project_validation_report.md", help="Markdown report path.")
    parser.add_argument("--basetemp-root", default=None, help="Root directory for pytest basetemp directories. Defaults to a system temp directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    full = bool(args.full)
    basetemp_root = Path(args.basetemp_root) if args.basetemp_root else None
    steps = run_validation(
        project_root=Path(args.project_root),
        full=full,
        skip_retrievers=args.skip_retrievers,
        json_report=Path(args.json_report),
        markdown_report=Path(args.markdown_report),
        basetemp_root=basetemp_root,
    )
    return 0 if all(step.returncode == 0 for step in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
