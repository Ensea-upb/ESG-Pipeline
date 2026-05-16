import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_contract_notes_document_reserved_evidence_types_and_contract_still_validates():
    notes = ROOT / "ESGInformationExtraction" / "docs" / "OUTPUT_CONTRACT_NOTES_V1_5.md"
    assert notes.exists()
    text = notes.read_text(encoding="utf-8")
    for value in ["list_item", "footnote", "caption", "unknown"]:
        assert value in text
    contract_before = json.loads((ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json").read_text(encoding="utf-8"))
    result = subprocess.run(
        [
            sys.executable,
            "ESGInformationExtraction/tools/validate_output_contract.py",
            "--output-dir",
            "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test",
            "--contract-path",
            "ESGInformationExtraction/contracts/output_contract_v1.json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout
    contract_after = json.loads((ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json").read_text(encoding="utf-8"))
    assert contract_before == contract_after
