from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from esg_csv_extraction import ESGCSVExtractor
from esg_table_extraction import ESGTableExtractor
from esg_visual_extraction import ESGVisualExtractor

from .audit import build_consolidated_audit, render_report
from .candidate_consolidator import consolidate_candidates
from .io_utils import utcnow, write_json
from .output_collector import collect_engine_outputs

log = logging.getLogger(__name__)


@dataclass
class FullExtractionResult:
    candidates_count: int
    output_dir: Path
    summary: dict[str, Any]


ENGINE_EXPECTED_FILES = {
    "csv": ["extraction_summary.json", "esg_information_candidates.csv"],
    "visual": ["visual_extraction_summary.json", "visual_candidates.csv"],
    "table": ["table_extraction_summary.json", "table_metric_candidates.csv"],
}


class FullExtractionRunner:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        overwrite: bool = False,
        reuse_existing: bool = False,
        force_rerun: bool = False,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.reuse_existing = reuse_existing
        self.force_rerun = force_rerun
        if reuse_existing and force_rerun:
            raise ValueError("--reuse-existing and --force-rerun cannot be used together")

    def run(self) -> FullExtractionResult:
        if self.output_dir.exists() and not self.overwrite and any(self.output_dir.iterdir()):
            raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
        started_at = utcnow()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        engine_runs = {
            "csv": self._run_or_reuse("csv", ESGCSVExtractor),
            "visual": self._run_or_reuse("visual", ESGVisualExtractor),
            "table": self._run_or_reuse("table", ESGTableExtractor),
        }
        collected = collect_engine_outputs(self.output_dir)
        consolidated = consolidate_candidates(collected, self.output_dir)
        audit = build_consolidated_audit(consolidated, self.output_dir)
        render_report(self.output_dir, collected, consolidated, audit)
        summary = {
            "schema_version": "1.0.0",
            "module": "ESGExtractionOrchestrator",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "started_at": started_at,
            "finished_at": utcnow(),
            "status": "success",
            "reuse_existing": self.reuse_existing,
            "force_rerun": self.force_rerun,
            "engine_run_manifest": engine_runs,
            "csv_candidates_count": engine_runs["csv"]["candidates_count"],
            "visual_candidates_count": engine_runs["visual"]["candidates_count"],
            "table_candidates_count": engine_runs["table"]["candidates_count"],
            "consolidated_candidates_count": len(consolidated),
            "unique_candidates_count": audit.get("unique_candidates_count", 0),
            "duplicate_candidates_count": audit.get("duplicate_candidates_count", 0),
            "duplicate_groups_count": audit.get("duplicate_groups_count", 0),
            "source_engine_distribution": audit.get("source_engine_distribution", {}),
            "information_type_distribution": audit.get("information_type_distribution", {}),
            "source_engine_information_type_distribution": audit.get("source_engine_information_type_distribution", {}),
            "deduplication_status_distribution": audit.get("deduplication_status_distribution", {}),
            "audit_errors_count": audit.get("errors_count", 0),
            "audit_warnings_count": audit.get("warnings_count", 0),
            "candidate_only": True,
            "review_required": True,
        }
        write_json(self.output_dir / "full_extraction_summary.json", summary)
        return FullExtractionResult(len(consolidated), self.output_dir, summary)

    def _run_or_reuse(self, engine_name: str, extractor_cls: Any) -> dict[str, Any]:
        engine_dir = self.output_dir / engine_name
        expected_files = ENGINE_EXPECTED_FILES[engine_name]
        if self.reuse_existing and self._engine_outputs_exist(engine_dir, expected_files):
            return {
                "engine": engine_name,
                "status": "reused_existing",
                "output_dir": str(engine_dir.resolve()),
                "candidates_count": self._candidate_count_from_existing(engine_name),
            }
        try:
            result = extractor_cls(self.input_dir, engine_dir, overwrite=self.overwrite or self.force_rerun).run()
        except Exception as exc:
            if engine_name == "visual":
                # Visual extraction is best-effort: log warning and continue with other engines.
                log.warning("Visual engine raised an unexpected exception (best-effort): %s", exc)
                return {
                    "engine": engine_name,
                    "status": "warning",
                    "output_dir": str(engine_dir.resolve()),
                    "candidates_count": 0,
                    "warning": str(exc),
                }
            raise
        engine_status = result.summary.get("status", "ran") if hasattr(result, "summary") and result.summary else "ran"
        base = {
            "engine": engine_name,
            "output_dir": str(engine_dir.resolve()),
            "candidates_count": result.candidates_count,
        }
        if engine_status == "warning":
            base["status"] = "warning"
            base["warning"] = result.summary.get("crop_pipeline_warning", "visual pipeline had crop warnings")
        else:
            base["status"] = "reran" if self.force_rerun else "ran"
        return base

    @staticmethod
    def _engine_outputs_exist(engine_dir: Path, expected_files: list[str]) -> bool:
        return engine_dir.exists() and all((engine_dir / name).exists() for name in expected_files)

    def _candidate_count_from_existing(self, engine_name: str) -> int:
        collected = collect_engine_outputs(self.output_dir)
        return len(collected.get(engine_name, {}).get("rows", []))
