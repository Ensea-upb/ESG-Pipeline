"""
pipeline_runner.py — Execute pipeline stages on a single document.
Writes outputs into the selected run_root under company/year/doc_type/canonical_id/.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Script paths relative to project root
_SCRIPTS = {
    "info_extraction":       "ESGInformationExtraction/run_pdf_extraction.py",
    "full_extraction":       "ESGExtractionOrchestrator/scripts/run_full_extraction.py",
    "indicator_validation":  "ESGIndicatorValidation/scripts/run_indicator_validation.py",
    "build_workspace":       "ESGManualReview/scripts/build_review_workspace.py",
}

STAGE_LABELS = {
    "info_extraction":      "Étape 1 — Information Extraction",
    "full_extraction":      "Étape 2 — Extraction CSV + Visuelle + Table",
    "indicator_validation": "Étape 3 — Validation des indicateurs",
    "build_workspace":      "Étape 4 — Construction de l'espace de revue",
}

STAGE_DESCRIPTIONS = {
    "info_extraction":      "Analyse le PDF et construit blocs de texte, tableaux, figures, store d'évidences.",
    "full_extraction":      "Lance les moteurs CSV, Visuel et Table pour extraire les candidats ESG.",
    "indicator_validation": "Valide et classe chaque candidat (possible_indicator / needs_review / reject_candidate).",
    "build_workspace":      "Construit le fichier de revue humaine (manual_review_workspace.csv).",
}

STAGE_ORDER = ["info_extraction", "full_extraction", "indicator_validation", "build_workspace"]


def compute_pdf_sha256(pdf_path: Path) -> str:
    """Compute SHA-256 hex digest of a PDF file."""
    h = hashlib.sha256()
    with pdf_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_canonical_id(sha256: str) -> str:
    """Derive canonical document ID from file SHA-256 (matches DocumentPostProcessing logic)."""
    digest = hashlib.sha256(f"canonical|{sha256}".encode("utf-8")).hexdigest()
    return f"canonical_{digest[:24]}"


def get_canonical_id_for_pdf(pdf_path: Path) -> str:
    return compute_canonical_id(compute_pdf_sha256(pdf_path))


def get_stage_dirs(
    run_root: Path, company: str, year: str, doc_type: str, canonical_id: str
) -> dict[str, Path]:
    """Return the expected output directory for each pipeline stage."""
    ws = run_root / company / year / doc_type / canonical_id
    return {
        "info_extraction":      ws / "01_information_extraction",
        "full_extraction":      ws / "02_orchestrator",
        "indicator_validation": ws / "03_validation",
        "build_workspace":      ws / "04_review_workspace",
    }


def stage_already_done(stage_dir: Path, stage: str) -> bool:
    """Return True if the stage output already exists with key files."""
    sentinel = {
        "info_extraction":      "extraction_summary.json",
        "full_extraction":      "csv/esg_information_candidates.csv",
        "indicator_validation": "indicator_validation_summary.json",
        "build_workspace":      "manual_review_workspace.csv",
    }
    key_file = stage_dir / sentinel.get(stage, "")
    return key_file.exists()


def run_stage(
    stage: str,
    stage_dirs: dict[str, Path],
    pdf_path: Path,
    canonical_id: str,
    company: str,
    year: str,
    doc_type: str,
    project_root: Path | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Run one pipeline stage as a subprocess. Returns result dict with status."""
    pr = project_root or _PROJECT_ROOT
    script = pr / _SCRIPTS[stage]

    if not script.exists():
        return {"status": "failed", "error": f"Script introuvable : {script}"}

    out_dir = stage_dirs[stage]
    out_dir.mkdir(parents=True, exist_ok=True)

    if stage == "info_extraction":
        args = [
            "--pdf-path",        str(pdf_path),
            "--document-id",     canonical_id,
            "--output-dir",      str(out_dir),
            "--company-slug",    company,
            "--fiscal-year",     year,
            "--official-doc-type", doc_type,
            "--overwrite",
        ]
    elif stage == "full_extraction":
        in_dir = stage_dirs["info_extraction"]
        args = [
            "--input-dir",  str(in_dir),
            "--output-dir", str(out_dir),
            "--overwrite",
        ]
    elif stage == "indicator_validation":
        in_dir = stage_dirs["full_extraction"]
        args = [
            "--input-dir",  str(in_dir),
            "--output-dir", str(out_dir),
            "--overwrite",
        ]
    elif stage == "build_workspace":
        in_dir = stage_dirs["indicator_validation"]
        args = [
            "--input-dir",  str(in_dir),
            "--output-dir", str(out_dir),
            "--overwrite",
        ]
    else:
        return {"status": "failed", "error": f"Stage inconnu : {stage}"}

    try:
        proc = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True,
            text=True,
            cwd=str(pr),
            timeout=timeout,
        )
        # Try to parse structured JSON output
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = {"status": "unknown", "raw_output": proc.stdout[-3000:]}

        if proc.returncode != 0 and parsed.get("status") not in ("success",):
            parsed["status"] = "failed"
            if proc.stderr:
                parsed["stderr"] = proc.stderr[-2000:]
        return parsed

    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": f"Timeout dépassé ({timeout}s). Essayez avec un PDF plus petit."}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def run_full_pipeline(
    pdf_path: Path,
    run_root: Path,
    company: str,
    year: str,
    doc_type: str,
    project_root: Path | None = None,
    stages: list[str] | None = None,
    timeout_per_stage: int = 600,
) -> dict[str, Any]:
    """
    Run the complete pipeline (or a subset of stages) for one document.
    Returns a dict mapping stage → result.
    """
    stages = stages or STAGE_ORDER
    canonical_id = get_canonical_id_for_pdf(pdf_path)
    stage_dirs = get_stage_dirs(run_root, company, year, doc_type, canonical_id)
    results: dict[str, Any] = {"canonical_id": canonical_id}

    for stage in stages:
        result = run_stage(
            stage, stage_dirs, pdf_path,
            canonical_id, company, year, doc_type,
            project_root, timeout_per_stage,
        )
        results[stage] = result
        if result.get("status") == "failed":
            results["pipeline_status"] = "failed"
            results["failed_at"] = stage
            return results

    results["pipeline_status"] = "success"
    return results
