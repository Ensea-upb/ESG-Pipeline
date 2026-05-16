#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGTableExtraction" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_table_extraction.contract import validate_table_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=True)
    args = parser.parse_args(argv)
    result = validate_table_outputs(Path(args.output_dir), Path(args.contract_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
