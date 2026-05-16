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

from esg_extraction_orchestrator.multi_document import run_multi_document_full_extraction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-documents", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run_multi_document_full_extraction(Path(args.input_root), Path(args.output_dir), overwrite=args.overwrite, max_documents=args.max_documents)
        print(json.dumps({"status": "success", "documents_tested_count": summary["documents_tested_count"], "consolidated_candidates_total": summary["consolidated_candidates_total"]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
