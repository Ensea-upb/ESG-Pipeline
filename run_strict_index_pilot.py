"""
run_strict_index_pilot.py
=========================
Strict-index pilot runner for the ESG pipeline.

Default behaviour: DRY-RUN (no subprocesses are launched).
Pass --execute to run for real.

Safety rules enforced:
  - Index filename MUST be "extraction_index_strict_likely_valid.csv"
  - --execute requires --max-documents
  - --max-documents cannot exceed 20
  - output-root must be empty (or --overwrite must be set)
  - No auto-accept logic anywhere in this file
  - No Internet calls
  - All outputs go under <output-root>/

Usage examples:
  # Dry-run (default)
  python run_strict_index_pilot.py \
      --index-path ".../extraction_index_strict_likely_valid.csv" \
      --output-root "PILOT_OUT" \
      --max-documents 5

  # Real run – prepare-review mode
  python run_strict_index_pilot.py \
      --index-path ".../extraction_index_strict_likely_valid.csv" \
      --output-root "PILOT_OUT" \
      --max-documents 5 \
      --execute

  # Real run – apply-review-and-build-dataset mode
  python run_strict_index_pilot.py \
      --index-path ".../extraction_index_strict_likely_valid.csv" \
      --output-root "PILOT_OUT" \
      --max-documents 5 \
      --mode apply-review-and-build-dataset \
      --decisions-root ".../decisions" \
      --execute
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_INDEX_FILENAME = "extraction_index_strict_likely_valid.csv"
MAX_DOCUMENTS_HARD_LIMIT = 20

VALID_MODES = ("prepare-review", "apply-review-and-build-dataset", "smoke-test-empty-review")

# Paths to the business-module CLI scripts (relative to the project root that
# contains this file).  All paths are resolved at runtime to absolute paths.
_HERE = Path(__file__).resolve().parent

SCRIPTS = {
    "run_pdf_extraction": _HERE / "ESGInformationExtraction" / "run_pdf_extraction.py",
    "validate_output_contract": _HERE / "ESGInformationExtraction" / "tools" / "validate_output_contract.py",
    "run_full_extraction": _HERE / "ESGExtractionOrchestrator" / "scripts" / "run_full_extraction.py",
    "validate_full_extraction": _HERE / "ESGExtractionOrchestrator" / "scripts" / "validate_full_extraction_outputs.py",
    "run_indicator_validation": _HERE / "ESGIndicatorValidation" / "scripts" / "run_indicator_validation.py",
    "validate_indicator_validation": _HERE / "ESGIndicatorValidation" / "scripts" / "validate_indicator_validation_outputs.py",
    "build_review_workspace": _HERE / "ESGManualReview" / "scripts" / "build_review_workspace.py",
    "apply_review_decisions": _HERE / "ESGManualReview" / "scripts" / "apply_review_decisions.py",
    "validate_manual_review": _HERE / "ESGManualReview" / "scripts" / "validate_manual_review_outputs.py",
    "build_indicator_database": _HERE / "ESGIndicatorDatabase" / "scripts" / "build_indicator_database.py",
    "validate_indicator_database": _HERE / "ESGIndicatorDatabase" / "scripts" / "validate_indicator_database_outputs.py",
    "build_esg_variables_dataset": _HERE / "ESGVariableDatasetBuilder" / "scripts" / "build_esg_variables_dataset.py",
    "validate_esg_variables_dataset": _HERE / "ESGVariableDatasetBuilder" / "scripts" / "validate_esg_variables_dataset.py",
}

CONTRACTS = {
    "output_contract_v1": _HERE / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json",
    "full_extraction_output_contract_v0": _HERE / "ESGExtractionOrchestrator" / "contracts" / "full_extraction_output_contract_v0.json",
    "indicator_validation_contract_v0": _HERE / "ESGIndicatorValidation" / "contracts" / "indicator_validation_contract_v0.json",
    "manual_review_contract_v0": _HERE / "ESGManualReview" / "contracts" / "manual_review_contract_v0.json",
    "indicator_database_contract_v0": _HERE / "ESGIndicatorDatabase" / "contracts" / "indicator_database_contract_v0.json",
    "esg_variables_dataset_contract_v0": _HERE / "ESGVariableDatasetBuilder" / "contracts" / "esg_variables_dataset_contract_v0.json",
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("strict_index_pilot")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ESG strict-index pilot runner (dry-run by default).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--index-path", required=True, help="Path to extraction_index_strict_likely_valid.csv")
    p.add_argument("--output-root", required=True, help="Root directory for all outputs")
    p.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help=f"Maximum number of documents to process (required for --execute; max {MAX_DOCUMENTS_HARD_LIMIT})",
    )
    p.add_argument("--corpus-run-id", default=None, help="Corpus run identifier (default: pilot_<YYYYMMDD_HHMMSS>)")
    p.add_argument("--company-slug", default=None, help="Filter by company slug")
    p.add_argument("--fiscal-year", default=None, help="Filter by fiscal year")
    p.add_argument("--doc-type", default=None, help="Filter by official_doc_type")
    p.add_argument(
        "--mode",
        default="prepare-review",
        choices=VALID_MODES,
        help="Pipeline mode (default: prepare-review)",
    )
    p.add_argument(
        "--decisions-root",
        default=None,
        help="Root directory containing human review decisions (required for apply-review-and-build-dataset)",
    )
    p.add_argument("--execute", action="store_true", default=False, help="Actually run the pipeline (default is dry-run)")
    p.add_argument("--overwrite", action="store_true", default=False, help="Allow overwriting an existing non-empty output-root")
    p.add_argument("--max-pages", type=int, default=None, help="Pass --max-pages to run_pdf_extraction.py")
    return p


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_args(args: argparse.Namespace) -> None:
    """Validate global arguments and raise SystemExit on any violation."""

    # Index filename check
    index_path = Path(args.index_path)
    if index_path.name != REQUIRED_INDEX_FILENAME:
        log.error(
            "Refused: index filename must be exactly '%s', got '%s'.",
            REQUIRED_INDEX_FILENAME,
            index_path.name,
        )
        sys.exit(1)

    # --execute requires --max-documents
    if args.execute and args.max_documents is None:
        log.error("Refused: --execute requires --max-documents to be set.")
        sys.exit(1)

    # Hard cap on --max-documents
    if args.max_documents is not None and args.max_documents > MAX_DOCUMENTS_HARD_LIMIT:
        log.error(
            "Refused: --max-documents=%d exceeds hard limit of %d.",
            args.max_documents,
            MAX_DOCUMENTS_HARD_LIMIT,
        )
        sys.exit(1)

    # apply-review-and-build-dataset requires --decisions-root
    if args.mode == "apply-review-and-build-dataset" and not args.decisions_root:
        log.error("Refused: mode 'apply-review-and-build-dataset' requires --decisions-root.")
        sys.exit(1)

    # output-root collision
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        if not args.overwrite:
            log.error(
                "Refused: output-root '%s' already exists and is non-empty. Use --overwrite to proceed.",
                output_root,
            )
            sys.exit(1)


# ---------------------------------------------------------------------------
# Index loading & filtering
# ---------------------------------------------------------------------------

def load_index(index_path: Path) -> list[dict]:
    """Load and return all rows from the index CSV."""
    rows = []
    with index_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def filter_documents(
    rows: list[dict],
    company_slug: str | None,
    fiscal_year: str | None,
    doc_type: str | None,
    max_documents: int | None,
) -> tuple[list[dict], list[dict]]:
    """
    Apply filters and return (selected, skipped).

    Rules:
    - final_file_exists must be "True"
    - optional slug / fiscal_year / doc_type filters
    - truncate to max_documents
    """
    selected = []
    skipped = []

    for row in rows:
        reasons = []

        if row.get("final_file_exists", "").strip() != "True":
            reasons.append("final_file_exists != True")

        if company_slug and row.get("company_slug", "").strip() != company_slug:
            reasons.append(f"company_slug filter (wanted {company_slug})")

        if fiscal_year and str(row.get("fiscal_year", "")).strip() != str(fiscal_year):
            reasons.append(f"fiscal_year filter (wanted {fiscal_year})")

        if doc_type and row.get("official_doc_type", "").strip() != doc_type:
            reasons.append(f"doc_type filter (wanted {doc_type})")

        if reasons:
            row = dict(row)
            row["_skip_reasons"] = "; ".join(reasons)
            skipped.append(row)
        else:
            selected.append(row)

    # Truncate
    if max_documents is not None and len(selected) > max_documents:
        extra = selected[max_documents:]
        for row in extra:
            row = dict(row)
            row["_skip_reasons"] = "max_documents limit reached"
            skipped.append(row)
        selected = selected[:max_documents]

    return selected, skipped


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def safe_name(s: str) -> str:
    """Replace characters that are unsafe in directory names."""
    return s.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")


def doc_output_dir(output_root: Path, row: dict) -> Path:
    doc_id_safe = safe_name(row["selected_canonical_document_id"])
    return (
        output_root
        / row["company_slug"]
        / str(row["fiscal_year"])
        / row["official_doc_type"]
        / doc_id_safe
    )


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

class CommandLog:
    """Append-only JSONL command log."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, step: str, command: list, returncode: int, duration_s: float, dry_run: bool) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "step": step,
            "command": command,
            "returncode": returncode,
            "duration_s": round(duration_s, 3),
            "dry_run": dry_run,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_step(
    step_name: str,
    cmd: list,
    log_file: Path,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    """
    Run a subprocess step.

    Returns (success, error_message).
    The first element of cmd MUST be sys.executable.
    """
    assert cmd[0] == sys.executable, "All subprocesses must start with sys.executable"

    log.info("[%s] %s", step_name, " ".join(str(c) for c in cmd))

    if dry_run:
        cmd_log.record(step_name, [str(c) for c in cmd], -1, 0.0, dry_run=True)
        return True, ""

    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        duration = time.monotonic() - t0
        cmd_log.record(step_name, [str(c) for c in cmd], -1, duration, dry_run=False)
        msg = f"Exception running step {step_name}: {exc}"
        log.error(msg)
        with log_file.open("w", encoding="utf-8") as fh:
            fh.write(f"EXCEPTION: {exc}\n")
        return False, msg

    duration = time.monotonic() - t0
    cmd_log.record(step_name, [str(c) for c in cmd], result.returncode, duration, dry_run=False)

    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    with log_file.open("w", encoding="utf-8") as fh:
        fh.write(combined)

    if result.returncode != 0:
        msg = f"Step {step_name} failed (rc={result.returncode}). See {log_file}"
        log.error(msg)
        return False, msg

    return True, ""


# ---------------------------------------------------------------------------
# top_review_candidates.csv builder
# ---------------------------------------------------------------------------

TOP_CANDIDATES_COLUMNS = [
    "company",
    "fiscal_year",
    "document_id",
    "official_doc_type",
    "page_number",
    "indicator_family",
    "indicator_key_candidate",
    "raw_value",
    "raw_unit",
    "normalized_value",
    "normalized_unit",
    "quote",
]

REVIEW_STATUS_PRIORITY = {
    "possible_indicator": 0,
    "needs_review": 1,
}


def build_top_review_candidates(workspace_dir: Path, row: dict, output_csv: Path) -> dict:
    """
    Read manual_review_workspace.csv (if it exists) from workspace_dir and
    produce top_review_candidates.csv sorted with possible_indicator first.

    Returns a summary dict.
    """
    workspace_csv = workspace_dir / "manual_review_workspace.csv"

    candidates: list[dict] = []

    if workspace_csv.exists():
        with workspace_csv.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                candidates.append(r)

    # Sort: possible_indicator first, then needs_review, then others
    def sort_key(c: dict) -> int:
        status = c.get("review_status", c.get("status", "")).strip().lower()
        return REVIEW_STATUS_PRIORITY.get(status, 99)

    candidates.sort(key=sort_key)

    nb_possible = sum(
        1 for c in candidates
        if c.get("review_status", c.get("status", "")).strip().lower() == "possible_indicator"
    )
    nb_needs_review = sum(
        1 for c in candidates
        if c.get("review_status", c.get("status", "")).strip().lower() == "needs_review"
    )

    # Write output CSV – emit only columns that exist, filling missing ones with ""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TOP_CANDIDATES_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for c in candidates:
            # Map workspace columns → target columns
            out_row = {
                "company": c.get("company", row.get("company_name", "")),
                "fiscal_year": c.get("fiscal_year", row.get("fiscal_year", "")),
                "document_id": c.get("document_id", row.get("selected_canonical_document_id", "")),
                "official_doc_type": c.get("official_doc_type", row.get("official_doc_type", "")),
                "page_number": c.get("page_number", ""),
                "indicator_family": c.get("indicator_family", ""),
                "indicator_key_candidate": c.get("indicator_key_candidate", c.get("indicator_key", "")),
                "raw_value": c.get("raw_value", ""),
                "raw_unit": c.get("raw_unit", ""),
                "normalized_value": c.get("normalized_value", ""),
                "normalized_unit": c.get("normalized_unit", ""),
                "quote": c.get("quote", ""),
            }
            writer.writerow(out_row)

    summary = {
        "nb_candidates": len(candidates),
        "nb_possible_indicator": nb_possible,
        "nb_needs_review": nb_needs_review,
    }
    return summary


# ---------------------------------------------------------------------------
# Smoke-test empty decisions builder
# ---------------------------------------------------------------------------

def build_empty_decisions_file(workspace_dir: Path, decisions_file: Path) -> None:
    """
    Create a decisions CSV with proposed_decision="" for every candidate.
    MUST NOT set proposed_decision to "accept_candidate".
    """
    workspace_csv = workspace_dir / "manual_review_workspace.csv"

    rows: list[dict] = []
    fieldnames: list[str] = []

    if workspace_csv.exists():
        with workspace_csv.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for r in reader:
                rows.append(r)

    # Ensure proposed_decision column exists
    if "proposed_decision" not in fieldnames:
        fieldnames.append("proposed_decision")

    decisions_file.parent.mkdir(parents=True, exist_ok=True)
    with decisions_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            r = dict(r)
            # Empty string — never "accept_candidate"
            r["proposed_decision"] = ""
            writer.writerow(r)


# ---------------------------------------------------------------------------
# Per-document pipeline steps
# ---------------------------------------------------------------------------

def step_01_information_extraction(
    row: dict,
    doc_out: Path,
    corpus_run_id: str,
    max_pages: int | None,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    out_dir = doc_out / "01_information_extraction"
    log_file = doc_out / "logs" / "step_01_information_extraction.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["run_pdf_extraction"]),
        "--pdf-path", row["final_path"],
        "--document-id", row["selected_canonical_document_id"],
        "--output-dir", str(out_dir),
        "--company", row["company_slug"],
        "--company-name", row["company_name"],
        "--company-slug", row["company_slug"],
        "--fiscal-year", str(row["fiscal_year"]),
        "--official-doc-type", row["official_doc_type"],
        "--final-path", row["final_path"],
        "--corpus-run-id", corpus_run_id,
    ]
    if max_pages is not None:
        cmd += ["--max-pages", str(max_pages)]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("01_information_extraction", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    # Validate
    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_output_contract"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["output_contract_v1"]),
    ]
    return run_step("01_validate_output_contract", val_cmd, log_file, cmd_log, dry_run)


def step_02_orchestrator(
    row: dict,
    doc_out: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    in_dir = doc_out / "01_information_extraction"
    out_dir = doc_out / "02_orchestrator"
    log_file = doc_out / "logs" / "step_02_orchestrator.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["run_full_extraction"]),
        "--input-dir", str(in_dir),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("02_orchestrator", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_full_extraction"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["full_extraction_output_contract_v0"]),
    ]
    return run_step("02_validate_full_extraction", val_cmd, log_file, cmd_log, dry_run)


def step_03_indicator_validation(
    row: dict,
    doc_out: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    in_dir = doc_out / "02_orchestrator"
    out_dir = doc_out / "03_validation"
    log_file = doc_out / "logs" / "step_03_validation.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["run_indicator_validation"]),
        "--input-dir", str(in_dir),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("03_indicator_validation", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_indicator_validation"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["indicator_validation_contract_v0"]),
    ]
    return run_step("03_validate_indicator_validation", val_cmd, log_file, cmd_log, dry_run)


def step_04_build_review_workspace(
    row: dict,
    doc_out: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    in_dir = doc_out / "03_validation"
    out_dir = doc_out / "04_review_workspace"
    log_file = doc_out / "logs" / "step_04_review_workspace.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["build_review_workspace"]),
        "--input-dir", str(in_dir),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    return run_step("04_build_review_workspace", cmd, log_file, cmd_log, dry_run)


def step_05_apply_review(
    row: dict,
    doc_out: Path,
    decisions_file: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    workspace_dir = doc_out / "04_review_workspace"
    out_dir = doc_out / "05_review_applied"
    log_file = doc_out / "logs" / "step_05_apply_review.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["apply_review_decisions"]),
        "--workspace-dir", str(workspace_dir),
        "--decisions-file", str(decisions_file),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("05_apply_review", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_manual_review"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["manual_review_contract_v0"]),
    ]
    return run_step("05_validate_manual_review", val_cmd, log_file, cmd_log, dry_run)


def step_06_indicator_database(
    row: dict,
    doc_out: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    in_dir = doc_out / "05_review_applied"
    out_dir = doc_out / "06_indicator_database"
    log_file = doc_out / "logs" / "step_06_indicator_database.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["build_indicator_database"]),
        "--input-dir", str(in_dir),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("06_indicator_database", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_indicator_database"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["indicator_database_contract_v0"]),
    ]
    return run_step("06_validate_indicator_database", val_cmd, log_file, cmd_log, dry_run)


def step_08_variable_dataset(
    output_root: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> tuple[bool, str]:
    in_root = output_root / "_indicator_databases"
    out_dir = output_root / "_variable_dataset"
    log_file = output_root / "logs" / "step_08_variable_dataset.log"

    cmd = [
        sys.executable,
        str(SCRIPTS["build_esg_variables_dataset"]),
        "--input-root", str(in_root),
        "--output-dir", str(out_dir),
    ]
    if overwrite:
        cmd.append("--overwrite")

    ok, err = run_step("08_variable_dataset", cmd, log_file, cmd_log, dry_run)
    if not ok:
        return False, err

    val_cmd = [
        sys.executable,
        str(SCRIPTS["validate_esg_variables_dataset"]),
        "--output-dir", str(out_dir),
        "--contract-path", str(CONTRACTS["esg_variables_dataset_contract_v0"]),
    ]
    return run_step("08_validate_variable_dataset", val_cmd, log_file, cmd_log, dry_run)


# ---------------------------------------------------------------------------
# Per-document processor
# ---------------------------------------------------------------------------

def process_document_prepare_review(
    row: dict,
    doc_out: Path,
    corpus_run_id: str,
    max_pages: int | None,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> dict:
    """Run steps 1-4 for one document (prepare-review mode)."""
    doc_record: dict = {
        "document_id": row["selected_canonical_document_id"],
        "company_slug": row["company_slug"],
        "company_name": row["company_name"],
        "fiscal_year": row["fiscal_year"],
        "official_doc_type": row["official_doc_type"],
        "final_path": row["final_path"],
        "status": "in_progress",
        "steps_completed": [],
        "error": None,
        "review_workspace_produced": False,
    }

    steps = [
        ("step_01", lambda: step_01_information_extraction(row, doc_out, corpus_run_id, max_pages, overwrite, cmd_log, dry_run)),
        ("step_02", lambda: step_02_orchestrator(row, doc_out, overwrite, cmd_log, dry_run)),
        ("step_03", lambda: step_03_indicator_validation(row, doc_out, overwrite, cmd_log, dry_run)),
        ("step_04", lambda: step_04_build_review_workspace(row, doc_out, overwrite, cmd_log, dry_run)),
    ]

    for step_id, step_fn in steps:
        ok, err = step_fn()
        if ok:
            doc_record["steps_completed"].append(step_id)
        else:
            doc_record["status"] = "failed"
            doc_record["error"] = err
            return doc_record

    # Produce top_review_candidates.csv and review_workspace_summary.json
    workspace_dir = doc_out / "04_review_workspace"
    top_csv = doc_out / "top_review_candidates.csv"
    summary_json = doc_out / "review_workspace_summary.json"

    if not dry_run:
        ws_summary = build_top_review_candidates(workspace_dir, row, top_csv)
        with summary_json.open("w", encoding="utf-8") as fh:
            json.dump(ws_summary, fh, indent=2, ensure_ascii=False)
        doc_record["review_workspace_produced"] = True
    else:
        doc_record["review_workspace_produced"] = False  # dry run: nothing produced

    doc_record["status"] = "success"
    return doc_record


def process_document_apply_review(
    row: dict,
    doc_out: Path,
    decisions_root: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> dict:
    """Run steps 5-6 for one document (apply-review-and-build-dataset mode)."""
    doc_record: dict = {
        "document_id": row["selected_canonical_document_id"],
        "company_slug": row["company_slug"],
        "company_name": row["company_name"],
        "fiscal_year": row["fiscal_year"],
        "official_doc_type": row["official_doc_type"],
        "final_path": row["final_path"],
        "status": "in_progress",
        "steps_completed": [],
        "error": None,
        "indicator_database_produced": False,
    }

    # Locate decisions file
    decisions_file = (
        decisions_root
        / row["company_slug"]
        / str(row["fiscal_year"])
        / row["official_doc_type"]
        / "review_decisions_filled.csv"
    )

    if not dry_run and not decisions_file.exists():
        doc_record["status"] = "skipped_no_decisions"
        log.warning(
            "No decisions file for %s/%s/%s: %s",
            row["company_slug"], row["fiscal_year"], row["official_doc_type"],
            decisions_file,
        )
        return doc_record

    ok, err = step_05_apply_review(row, doc_out, decisions_file, overwrite, cmd_log, dry_run)
    if ok:
        doc_record["steps_completed"].append("step_05")
    else:
        doc_record["status"] = "failed"
        doc_record["error"] = err
        return doc_record

    ok, err = step_06_indicator_database(row, doc_out, overwrite, cmd_log, dry_run)
    if ok:
        doc_record["steps_completed"].append("step_06")
    else:
        doc_record["status"] = "failed"
        doc_record["error"] = err
        return doc_record

    doc_record["indicator_database_produced"] = True
    doc_record["status"] = "success"
    return doc_record


def process_document_smoke_test(
    row: dict,
    doc_out: Path,
    overwrite: bool,
    cmd_log: CommandLog,
    dry_run: bool,
) -> dict:
    """
    Smoke-test mode: generate empty decisions, then apply steps 5-6.
    proposed_decision is NEVER set to "accept_candidate".
    """
    doc_record: dict = {
        "document_id": row["selected_canonical_document_id"],
        "company_slug": row["company_slug"],
        "company_name": row["company_name"],
        "fiscal_year": row["fiscal_year"],
        "official_doc_type": row["official_doc_type"],
        "final_path": row["final_path"],
        "status": "in_progress",
        "steps_completed": [],
        "error": None,
        "indicator_database_produced": False,
    }

    # Build empty decisions in a temp location inside doc_out
    workspace_dir = doc_out / "04_review_workspace"
    empty_decisions_file = doc_out / "smoke_test_empty_decisions.csv"

    if not dry_run:
        build_empty_decisions_file(workspace_dir, empty_decisions_file)

    ok, err = step_05_apply_review(row, doc_out, empty_decisions_file, overwrite, cmd_log, dry_run)
    if ok:
        doc_record["steps_completed"].append("step_05")
    else:
        doc_record["status"] = "failed"
        doc_record["error"] = err
        return doc_record

    ok, err = step_06_indicator_database(row, doc_out, overwrite, cmd_log, dry_run)
    if ok:
        doc_record["steps_completed"].append("step_06")
    else:
        doc_record["status"] = "failed"
        doc_record["error"] = err
        return doc_record

    doc_record["indicator_database_produced"] = True
    doc_record["status"] = "success"
    return doc_record


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_csv_list(path: Path, rows: list[dict], extra_fields: list[str] | None = None) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # Collect all fieldnames
    all_keys: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    if extra_fields:
        for k in extra_fields:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_report_md(summary: dict) -> str:
    lines = [
        "# ESG Strict-Index Pilot Run Report",
        "",
        f"**Corpus Run ID:** {summary['corpus_run_id']}",
        f"**Mode:** {summary['mode']}",
        f"**Date:** {datetime.utcnow().isoformat()}Z",
        f"**Dry run:** {summary['dry_run']}",
        f"**Execute:** {summary['execute']}",
        "",
        "## Filters",
        f"- company_slug: {summary['filters']['company_slug']}",
        f"- fiscal_year: {summary['filters']['fiscal_year']}",
        f"- doc_type: {summary['filters']['doc_type']}",
        "",
        "## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Documents selected | {summary['documents_selected']} |",
        f"| Documents processed | {summary['documents_processed']} |",
        f"| Documents success | {summary['documents_success']} |",
        f"| Documents failed | {summary['documents_failed']} |",
        f"| Documents skipped | {summary['documents_skipped']} |",
        f"| Review workspaces produced | {summary['review_workspaces_produced']} |",
        f"| Indicator databases produced | {summary['indicator_databases_produced']} |",
        f"| Variable dataset produced | {summary['variable_dataset_produced']} |",
        f"| Found values count | {summary['found_values_count']} |",
        "",
        "## Per-document Results",
        "",
        "| document_id | company | fiscal_year | doc_type | status | error |",
        "|-------------|---------|-------------|----------|--------|-------|",
    ]
    for d in summary.get("per_document", []):
        lines.append(
            f"| {d['document_id']} | {d['company_slug']} | {d['fiscal_year']} "
            f"| {d['official_doc_type']} | {d['status']} | {d.get('error') or ''} |"
        )
    lines += ["", "---", "*Generated by run_strict_index_pilot.py*", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------ #
    # Global safety checks                                                #
    # ------------------------------------------------------------------ #
    validate_args(args)

    dry_run = not args.execute
    corpus_run_id = args.corpus_run_id or f"pilot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    index_path = Path(args.index_path).resolve()
    output_root = Path(args.output_root).resolve()
    decisions_root = Path(args.decisions_root).resolve() if args.decisions_root else None

    log.info("=== ESG Strict-Index Pilot Runner ===")
    log.info("corpus_run_id : %s", corpus_run_id)
    log.info("mode          : %s", args.mode)
    log.info("dry_run       : %s", dry_run)
    log.info("index_path    : %s", index_path)
    log.info("output_root   : %s", output_root)

    # ------------------------------------------------------------------ #
    # Load & filter index                                                 #
    # ------------------------------------------------------------------ #
    all_rows = load_index(index_path)
    log.info("Loaded %d rows from index.", len(all_rows))

    selected, skipped = filter_documents(
        all_rows,
        company_slug=args.company_slug,
        fiscal_year=args.fiscal_year,
        doc_type=args.doc_type,
        max_documents=args.max_documents,
    )

    if not selected:
        log.error("No documents selected after filtering. Aborting.")
        sys.exit(1)

    log.info("Selected %d document(s), skipped %d.", len(selected), len(skipped))

    # ------------------------------------------------------------------ #
    # Prepare output-root                                                 #
    # ------------------------------------------------------------------ #
    output_root.mkdir(parents=True, exist_ok=True)
    cmd_log = CommandLog(output_root / "pilot_command_log.jsonl")

    # ------------------------------------------------------------------ #
    # Initial summary skeleton                                            #
    # ------------------------------------------------------------------ #
    summary: dict = {
        "corpus_run_id": corpus_run_id,
        "mode": args.mode,
        "index_path": str(index_path),
        "filters": {
            "company_slug": args.company_slug,
            "fiscal_year": args.fiscal_year,
            "doc_type": args.doc_type,
        },
        "dry_run": dry_run,
        "execute": args.execute,
        "max_documents": args.max_documents,
        "documents_selected": len(selected),
        "documents_processed": 0,
        "documents_success": 0,
        "documents_failed": 0,
        "documents_skipped": 0,
        "review_workspaces_produced": 0,
        "indicator_databases_produced": 0,
        "variable_dataset_produced": False,
        "found_values_count": None,
        "per_document": [],
        "output_root": str(output_root),
    }

    # Dry-run: populate per_document with status="dry_run_selected" and stop
    if dry_run:
        for row in selected:
            summary["per_document"].append(
                {
                    "document_id": row["selected_canonical_document_id"],
                    "company_slug": row["company_slug"],
                    "company_name": row["company_name"],
                    "fiscal_year": row["fiscal_year"],
                    "official_doc_type": row["official_doc_type"],
                    "final_path": row["final_path"],
                    "status": "dry_run_selected",
                    "steps_completed": [],
                    "error": None,
                }
            )
        _write_run_outputs(output_root, summary, selected, skipped, [])
        log.info("DRY-RUN complete. pilot_run_summary.json written to %s", output_root)
        return

    # ------------------------------------------------------------------ #
    # Real execution                                                      #
    # ------------------------------------------------------------------ #
    per_doc_records: list[dict] = []
    indicator_db_dirs: list[Path] = []

    for row in selected:
        doc_out = doc_output_dir(output_root, row)
        doc_out.mkdir(parents=True, exist_ok=True)
        (doc_out / "logs").mkdir(parents=True, exist_ok=True)

        log.info(
            "--- Processing %s / %s / %s ---",
            row["company_slug"], row["fiscal_year"], row["official_doc_type"],
        )

        if args.mode == "prepare-review":
            record = process_document_prepare_review(
                row, doc_out, corpus_run_id,
                max_pages=args.max_pages,
                overwrite=args.overwrite,
                cmd_log=cmd_log,
                dry_run=False,
            )
        elif args.mode == "apply-review-and-build-dataset":
            record = process_document_apply_review(
                row, doc_out,
                decisions_root=decisions_root,  # type: ignore[arg-type]
                overwrite=args.overwrite,
                cmd_log=cmd_log,
                dry_run=False,
            )
        elif args.mode == "smoke-test-empty-review":
            record = process_document_smoke_test(
                row, doc_out,
                overwrite=args.overwrite,
                cmd_log=cmd_log,
                dry_run=False,
            )
        else:
            raise ValueError(f"Unknown mode: {args.mode}")  # pragma: no cover

        per_doc_records.append(record)

        # Aggregate step-7: copy indicator_database to _indicator_databases/
        if record.get("indicator_database_produced"):
            db_src = doc_out / "06_indicator_database"
            slug_safe = safe_name(row["company_slug"])
            fy_safe = safe_name(str(row["fiscal_year"]))
            dt_safe = safe_name(row["official_doc_type"])
            did_safe = safe_name(row["selected_canonical_document_id"])
            db_dst = output_root / "_indicator_databases" / f"{slug_safe}__{fy_safe}__{dt_safe}__{did_safe}"
            if db_dst.exists() and args.overwrite:
                shutil.rmtree(db_dst)
            shutil.copytree(str(db_src), str(db_dst))
            indicator_db_dirs.append(db_dst)

    # ------------------------------------------------------------------ #
    # Step 8: variable dataset (apply-review and smoke-test only)         #
    # ------------------------------------------------------------------ #
    variable_dataset_produced = False
    if args.mode in ("apply-review-and-build-dataset", "smoke-test-empty-review"):
        if indicator_db_dirs:
            ok, err = step_08_variable_dataset(output_root, args.overwrite, cmd_log, dry_run=False)
            if ok:
                variable_dataset_produced = True
            else:
                log.error("Variable dataset build failed: %s", err)

    # ------------------------------------------------------------------ #
    # Aggregate summary                                                   #
    # ------------------------------------------------------------------ #
    n_success = sum(1 for r in per_doc_records if r["status"] == "success")
    n_failed = sum(1 for r in per_doc_records if r["status"] == "failed")
    n_skipped = sum(1 for r in per_doc_records if r["status"] == "skipped_no_decisions")
    n_ws = sum(1 for r in per_doc_records if r.get("review_workspace_produced"))
    n_db = sum(1 for r in per_doc_records if r.get("indicator_database_produced"))

    summary.update(
        {
            "documents_processed": len(per_doc_records),
            "documents_success": n_success,
            "documents_failed": n_failed,
            "documents_skipped": n_skipped,
            "review_workspaces_produced": n_ws,
            "indicator_databases_produced": n_db,
            "variable_dataset_produced": variable_dataset_produced,
            "per_document": per_doc_records,
        }
    )

    _write_run_outputs(output_root, summary, selected, skipped, per_doc_records)

    log.info("=== Run complete ===")
    log.info(
        "Success: %d  Failed: %d  Skipped: %d",
        n_success, n_failed, n_skipped,
    )


def _write_run_outputs(
    output_root: Path,
    summary: dict,
    selected: list[dict],
    skipped: list[dict],
    per_doc_records: list[dict],
) -> None:
    """Write all top-level output files."""
    # pilot_run_summary.json
    with (output_root / "pilot_run_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    # pilot_run_report.md
    (output_root / "pilot_run_report.md").write_text(
        build_report_md(summary), encoding="utf-8"
    )

    # selected_documents.csv
    write_csv_list(output_root / "selected_documents.csv", selected)

    # skipped_documents.csv
    write_csv_list(output_root / "skipped_documents.csv", skipped)

    # failed_documents.csv
    failed = [r for r in per_doc_records if r.get("status") == "failed"]
    write_csv_list(output_root / "failed_documents.csv", failed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
