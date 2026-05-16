#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGIndicatorValidation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_indicator_validation.multi_document_audit import run_multi_document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-documents", type=int)
    args = parser.parse_args(argv)
    try:
        summary = run_multi_document(Path(args.input_root), Path(args.output_dir), overwrite=args.overwrite, max_documents=args.max_documents)
        print(json.dumps({"status": "success", **summary}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
