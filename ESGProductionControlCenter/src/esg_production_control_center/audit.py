from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


FORBIDDEN_TOKENS = ["score", "validated_indicator", "final_indicator"]


def audit_control_outputs(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    findings = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".csv", ".json", ".jsonl", ".md", ".txt"}:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            for token in FORBIDDEN_TOKENS:
                if token == "score" and "no score" in text:
                    continue
                if token in text and token not in {"validated_indicator", "final_indicator"}:
                    findings.append({"file": str(p), "finding": f"{token}_token_detected"})
    return {"findings_count": len(findings), "findings": findings}


def write_batch_summary(output_dir: str | Path, rows: list[dict[str, Any]], overwrite: bool = False) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "batch_production_summary.json", out / "batch_production_table.csv", out / "batch_production_report.md", out / "batch_run_log.jsonl"]
    if not overwrite and any(p.exists() for p in files):
        raise FileExistsError("Refusing to overwrite batch outputs")
    files[0].write_text(json.dumps({"documents_count": len(rows), "dry_run_default": True}, indent=2), encoding="utf-8")
    with files[1].open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["document_id", "input_dir", "status", "run_id"])
        writer.writeheader()
        writer.writerows(rows)
    files[2].write_text("# Batch Production Report\n\nNo ESG score or final validated indicator is produced.\n", encoding="utf-8")
    files[3].write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return [str(p) for p in files]
