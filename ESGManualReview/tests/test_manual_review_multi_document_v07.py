import json
import subprocess
import sys

from .helpers import MULTI, ROOT, hash_tree, make_indicator_output


def test_multi_document_manual_review_audit(tmp_path):
    root = tmp_path / "inputs"
    make_indicator_output(root / "doc1")
    make_indicator_output(root / "doc2")
    before = hash_tree(root)
    out = tmp_path / "multi"
    result = subprocess.run([sys.executable, str(MULTI), "--input-root", str(root), "--output-dir", str(out), "--overwrite"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["documents_tested_count"] == 2
    assert payload["real_world_manual_review_pending"] is True
    assert (out / "multi_document_manual_review_summary.json").exists()
    assert (out / "multi_document_manual_review.csv").exists()
    assert (out / "multi_document_manual_review.md").exists()
    assert before == hash_tree(root)
