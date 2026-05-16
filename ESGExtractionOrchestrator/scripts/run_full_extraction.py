#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for rel in ["ESGExtractionOrchestrator/src", "ESGCSVExtraction/src", "ESGVisualExtraction/src", "ESGTableExtraction/src"]:
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from esg_extraction_orchestrator import FullExtractionRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-existing", action="store_true", help="Reuse existing csv/visual/table sub-engine outputs when all required files are present.")
    parser.add_argument("--force-rerun", action="store_true", help="Force sub-engines to rerun even if reusable outputs exist.")
    args = parser.parse_args(argv)
    try:
        result = FullExtractionRunner(
            Path(args.input_dir),
            Path(args.output_dir),
            overwrite=args.overwrite,
            reuse_existing=args.reuse_existing,
            force_rerun=args.force_rerun,
        ).run()
        print(json.dumps({
            "status": "success",
            "output_dir": str(result.output_dir),
            "consolidated_candidates_count": result.candidates_count,
            "unique_candidates_count": result.summary.get("unique_candidates_count", 0),
            "duplicate_candidates_count": result.summary.get("duplicate_candidates_count", 0),
            "source_engine_distribution": result.summary.get("source_engine_distribution", {}),
            "engine_run_manifest": result.summary.get("engine_run_manifest", {}),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
