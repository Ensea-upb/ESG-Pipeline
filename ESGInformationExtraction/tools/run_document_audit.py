#!/usr/bin/env python
"""Regenerate document audit outputs from an existing extraction directory.

This CLI does not open or parse the source PDF. It only reads existing
JSON/JSONL outputs and rewrites the three v0.8 audit files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ESGInformationExtraction.run_pdf_extraction import regenerate_document_audit_from_output_dir
from ESGInformationExtraction.tools.validate_output_contract import validate_contract


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate v0.8 document audit outputs.")
    parser.add_argument("--output-dir", required=True, help="Existing PDF extraction output directory.")
    parser.add_argument("--overwrite", action="store_true", help="Rewrite audit outputs if they already exist.")
    parser.add_argument("--strict", action="store_true", help="Promote audit warnings to failure.")
    parser.add_argument("--quiet", action="store_true", help="Only print the final JSON summary.")
    parser.add_argument("--contract-path", default=None, help="Optional output contract JSON to validate after audit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return_code, payload = regenerate_document_audit_from_output_dir(
        output_dir=Path(args.output_dir),
        overwrite=args.overwrite,
        strict=args.strict,
    )
    if args.contract_path:
        contract_code, contract_payload = validate_contract(Path(args.output_dir), Path(args.contract_path))
        payload["contract_validation_status"] = contract_payload.get("status")
        payload["contract_validation_errors_count"] = contract_payload.get("errors_count")
        report_path = Path(args.output_dir) / "consistency_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["contract_validation"] = contract_payload
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if contract_code != 0 and return_code == 0:
            return_code = contract_code
            payload["status"] = "failed"
    print(json.dumps(payload, ensure_ascii=False, indent=None if args.quiet else 2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
