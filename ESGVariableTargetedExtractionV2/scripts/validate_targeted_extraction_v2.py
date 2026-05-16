"""
validate_targeted_extraction_v2.py — Validate V2 outputs against contract.

Usage:
    python ESGVariableTargetedExtractionV2/scripts/validate_targeted_extraction_v2.py \\
        --output-dir "ESGVariableTargetedExtractionV2/outputs/..." \\
        --contract-path "ESGVariableTargetedExtractionV2/contracts/targeted_candidates_v2_contract.json"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.validators import validate_output_dir
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.io_utils import read_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate ESGVariableTargetedExtractionV2 outputs")
    p.add_argument("--output-dir", required=True, help="V2 output directory to validate")
    p.add_argument("--contract-path", default=None,
                   help="Path to targeted_candidates_v2_contract.json")
    return p.parse_args()


def main() -> dict:
    args = parse_args()
    output_dir = Path(args.output_dir)

    if not output_dir.exists():
        result = {"status": "failed", "error": f"output_dir not found: {output_dir}"}
        print(json.dumps(result))
        return result

    contract_path = args.contract_path
    if contract_path is None:
        default_contract = _ROOT / "ESGVariableTargetedExtractionV2" / "contracts" / "targeted_candidates_v2_contract.json"
        if default_contract.exists():
            contract_path = str(default_contract)

    result = validate_output_dir(output_dir, contract_path)

    # Also check summary
    summary_path = output_dir / "extraction_v2_summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        result["summary_document_id"] = summary.get("document_id", "")
        result["summary_company"] = summary.get("company", "")
        result["summary_fiscal_year"] = summary.get("fiscal_year", "")
        result["summary_candidates_found"] = summary.get("candidates_found", 0)
        result["summary_embedding_backend"] = summary.get("embedding_backend_status", "")

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
