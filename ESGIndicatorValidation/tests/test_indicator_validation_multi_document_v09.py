import json
import subprocess
import sys

from .helpers import ROOT, hash_tree, make_orchestrator_output


def test_multi_document_indicator_validation(tmp_path):
    root = tmp_path / "inputs"
    make_orchestrator_output(root / "doc1")
    make_orchestrator_output(root / "doc2")
    before = hash_tree(root)
    out = tmp_path / "multi"
    script = ROOT / "ESGIndicatorValidation" / "scripts" / "run_multi_document_indicator_validation.py"
    result = subprocess.run([sys.executable, str(script), "--input-root", str(root), "--output-dir", str(out), "--overwrite"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["documents_tested_count"] == 2
    assert (out / "multi_document_indicator_validation_summary.json").exists()
    assert (out / "multi_document_indicator_validation.csv").exists()
    assert (out / "multi_document_indicator_validation.md").exists()
    assert before == hash_tree(root)
