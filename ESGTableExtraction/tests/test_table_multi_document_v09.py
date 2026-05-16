import json
import subprocess
import sys
from pathlib import Path
from .helpers import CONTRACT, MULTI, hash_tree, make_input


def test_multi_document_table_audit(tmp_path: Path):
    root = tmp_path / "inputs"
    root.mkdir()
    make_input(root / "doc1")
    make_input(root / "doc2")
    before = hash_tree(root)
    out = tmp_path / "multi"
    result = subprocess.run([sys.executable, str(MULTI), "--input-root", str(root), "--output-dir", str(out), "--contract-path", str(CONTRACT), "--overwrite"], cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    assert (out / "multi_document_table_audit_summary.json").exists()
    assert (out / "multi_document_table_audit.csv").exists()
    assert (out / "multi_document_table_audit.md").exists()
    payload = json.loads((out / "multi_document_table_audit_summary.json").read_text(encoding="utf-8"))
    assert payload["documents_tested_count"] == 2
    assert payload["candidates_count_total"] > 0
    assert before == hash_tree(root)
