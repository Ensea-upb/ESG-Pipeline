from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_MARKERS: dict[str, dict[str, Any]] = {
    "ESGInformationExtraction": {
        "root": "ESGInformationExtraction/outputs",
        "markers": ["document_record.json", "extraction_summary.json", "evidence_store.jsonl"],
        "contract": "ESGInformationExtraction/contracts/output_contract_v1.json",
        "next": ["ESGExtractionOrchestrator", "ESGCSVExtraction", "ESGVisualExtraction", "ESGTableExtraction"],
    },
    "ESGExtractionOrchestrator": {
        "root": "ESGExtractionOrchestrator/outputs",
        "markers": ["consolidated_candidates.csv", "full_extraction_summary.json"],
        "contract": "ESGExtractionOrchestrator/contracts/full_extraction_output_contract_v0.json",
        "next": ["ESGIndicatorValidation"],
    },
    "ESGIndicatorValidation": {
        "root": "ESGIndicatorValidation/outputs",
        "markers": ["indicator_candidate_validations.csv", "validation_review_queue.csv"],
        "contract": "ESGIndicatorValidation/contracts/indicator_validation_contract_v0.json",
        "next": ["ESGManualReview"],
    },
    "ESGManualReview": {
        "root": "ESGManualReview/outputs",
        "markers": ["manual_review_workspace.csv", "accepted_candidate_inputs.csv", "reviewed_candidates.csv"],
        "contract": "ESGManualReview/contracts/manual_review_contract_v0.json",
        "next": ["ESGIndicatorDatabase"],
    },
    "ESGIndicatorDatabase": {
        "root": "ESGIndicatorDatabase/outputs",
        "markers": ["indicator_preparation_database.csv", "indicator_database_summary.json"],
        "contract": "ESGIndicatorDatabase/contracts/indicator_database_contract_v0.json",
        "next": [],
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _metadata(output_dir: Path) -> dict[str, Any]:
    for name in ["extraction_summary.json", "full_extraction_summary.json", "indicator_validation_summary.json", "manual_review_summary.json", "indicator_database_summary.json", "document_record.json"]:
        data = _read_json(output_dir / name)
        if data:
            return {
                "document_id": data.get("document_id") or data.get("input_document_id"),
                "company": data.get("company") or data.get("company_name"),
                "fiscal_year": data.get("fiscal_year"),
            }
    return {"document_id": None, "company": None, "fiscal_year": None}


def discover_outputs(project_root: str | Path = ".") -> list[dict[str, Any]]:
    root = Path(project_root).resolve()
    discovered: list[dict[str, Any]] = []
    for module_name, spec in MODULE_MARKERS.items():
        module_root = root / spec["root"]
        if not module_root.exists():
            continue
        for candidate in sorted(p for p in module_root.rglob("*") if p.is_dir()):
            if candidate.name in {"__pycache__", ".pytest_tmp"}:
                continue
            found = [m for m in spec["markers"] if (candidate / m).exists()]
            if not found:
                continue
            meta = _metadata(candidate)
            discovered.append({
                "module_name": module_name,
                "output_dir": str(candidate),
                "detected_status": "detected",
                "document_id": meta["document_id"],
                "company": meta["company"],
                "fiscal_year": meta["fiscal_year"],
                "main_files_found": found,
                "contract_file_expected": str(root / spec["contract"]),
                "can_be_used_as_input_for": spec["next"],
                "warnings": [],
            })
    return discovered


def write_discovery_outputs(output_dir: str | Path, outputs: list[dict[str, Any]], overwrite: bool = False) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "control_center_inventory.json", out / "discovered_outputs.jsonl", out / "discovery_summary.json"]
    if not overwrite:
        existing = [str(p) for p in files if p.exists()]
        if existing:
            raise FileExistsError(f"Refusing to overwrite existing discovery files: {existing}")
    summary = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outputs_count": len(outputs),
        "modules": sorted({o["module_name"] for o in outputs}),
    }
    files[0].write_text(json.dumps({"summary": summary, "outputs": outputs}, indent=2), encoding="utf-8")
    files[1].write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outputs), encoding="utf-8")
    files[2].write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return [str(p) for p in files]
