import json
import subprocess
import sys

from .helpers import MULTI, ROOT, hash_tree, make_manual_review_output


def test_multi_document_database(tmp_path):
    root = tmp_path / "inputs"
    make_manual_review_output(root / "doc1")
    make_manual_review_output(root / "doc2", accepted=False)
    before = hash_tree(root)
    out = tmp_path / "multi"
    result = subprocess.run([sys.executable, str(MULTI), "--input-root", str(root), "--output-dir", str(out), "--overwrite"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["documents_tested_count"] == 2
    assert payload["empty_databases_count"] == 1
    assert (out / "multi_document_indicator_database_summary.json").exists()
    assert (out / "multi_document_indicator_database.csv").exists()
    assert (out / "multi_document_indicator_database.md").exists()
    assert before == hash_tree(root)
