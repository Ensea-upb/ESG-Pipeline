#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "ESGCSVExtraction" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_csv_extraction.multi_document_audit import run_multi_document_audit


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ESGCSVExtraction on multiple documentary output folders.")
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-documents", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = run_multi_document_audit(
            input_root=Path(args.input_root),
            output_dir=Path(args.output_dir),
            overwrite=args.overwrite,
            max_documents=args.max_documents,
        )
        print(json.dumps({
            "status": "success",
            "documents_tested_count": summary["documents_tested_count"],
            "total_candidates_count": summary["total_candidates_count"],
            "information_type_distribution": summary["information_type_distribution"],
            "gate_decision": summary["gate_decision"],
            "output_dir": summary["output_dir"],
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
