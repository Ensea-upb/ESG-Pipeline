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

from esg_extraction_orchestrator.contract import validate_full_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=True)
    args = parser.parse_args(argv)
    result = validate_full_outputs(Path(args.output_dir), Path(args.contract_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
