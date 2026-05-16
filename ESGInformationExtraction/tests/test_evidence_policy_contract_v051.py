"""Non-regression tests for the v0.4.2 evidence-policy contract.

Every evidence in evidence_store.jsonl, regardless of its evidence_type
(section_heading, paragraph, table, …), must carry the five v0.4.2 fields
introduced in propagate_section_quality_to_evidence.

Regression context: v0.5 added table evidences that were created after
propagate_section_quality_to_evidence ran, so they were missing these fields.
"""
from __future__ import annotations

from pathlib import Path

from .conftest import read_jsonl, run_cli, write_test_pdf


# ── fixtures ─────────────────────────────────────────────────────────────────

V042_FIELDS = {
    "section_quality_score",
    "section_is_suspicious",
    "section_suspicion_reasons",
    "evidence_policy",
    "is_quarantined_evidence",
}


def _suspicious_mismatch_pdf(tmp_path: Path) -> Path:
    """PDF whose only section is a mismatch (CERTIFICATION + unrelated body text)."""
    return write_test_pdf(
        tmp_path / "policy_contract_mismatch.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "This document is a free translation for readers.",
            "The history of the group includes brands and maisons.",
            "Chronology and brand names are presented in this part.",
            "LVMH brands and historical background continue here.",
        ]],
    )


def _table_like_mismatch_pdf(tmp_path: Path) -> Path:
    """PDF with table-like keywords in a mismatch section, to force table evidences."""
    return write_test_pdf(
        tmp_path / "policy_contract_table.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "total emissions scope 1 tco2 headcount revenue eur million",
            "breakdown by region consumption gwh mwh ratio",
            "employees scope 2 amount subtotal count",
        ]],
    )


# ── A: all evidences carry the five v0.4.2 fields ────────────────────────────

def test_all_evidences_have_v042_fields_small_pdf(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="contract_small")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    for ev in evidence:
        missing = V042_FIELDS - ev.keys()
        assert not missing, (
            f"evidence_type={ev.get('evidence_type')} id={ev.get('evidence_id')} "
            f"missing fields: {missing}"
        )


def test_all_evidences_have_v042_fields_mismatch_pdf(require_pdfplumber, tmp_path: Path):
    pdf = _suspicious_mismatch_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="contract_mismatch")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    for ev in evidence:
        missing = V042_FIELDS - ev.keys()
        assert not missing, (
            f"evidence_type={ev.get('evidence_type')} id={ev.get('evidence_id')} "
            f"missing fields: {missing}"
        )


def test_all_evidences_have_v042_fields_table_like_pdf(require_pdfplumber, tmp_path: Path):
    pdf = _table_like_mismatch_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="contract_table")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    for ev in evidence:
        missing = V042_FIELDS - ev.keys()
        assert not missing, (
            f"evidence_type={ev.get('evidence_type')} id={ev.get('evidence_id')} "
            f"missing fields: {missing}"
        )


# ── B: table evidences specifically carry all v0.4.2 fields ──────────────────

def test_table_evidences_have_v042_fields(require_pdfplumber, tmp_path: Path):
    """Table evidences are the regression-prone type — check explicitly."""
    pdf = _table_like_mismatch_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="contract_table_ev")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    table_ev = [e for e in evidence if e.get("evidence_type") == "table"]
    if not table_ev:
        return  # no table detected on this run — contract still holds vacuously
    for ev in table_ev:
        missing = V042_FIELDS - ev.keys()
        assert not missing, f"Table evidence {ev.get('evidence_id')} missing fields: {missing}"


# ── C: quarantined evidences have consistent flags ───────────────────────────

def test_quarantined_evidences_flags_consistent(require_pdfplumber, tmp_path: Path):
    pdf = _suspicious_mismatch_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="contract_quarantine")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    quarantined = [e for e in evidence if e.get("evidence_policy") == "quarantine"]
    for ev in quarantined:
        assert ev["is_quarantined_evidence"] is True, (
            f"evidence_type={ev.get('evidence_type')} has policy=quarantine "
            f"but is_quarantined_evidence={ev.get('is_quarantined_evidence')}"
        )
        assert ev["review_required"] is True, (
            f"evidence_type={ev.get('evidence_type')} quarantined but review_required is not True"
        )


# ── D: section-linked evidences inherit section policy ───────────────────────

def test_section_policy_propagated_to_all_linked_evidences(require_pdfplumber, tmp_path: Path):
    pdf = _suspicious_mismatch_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="contract_propagate")
    assert result.returncode == 0, result.stderr
    sections = read_jsonl(out / "section_index.jsonl")
    evidence = read_jsonl(out / "evidence_store.jsonl")
    sections_with_policy = [s for s in sections if s.get("evidence_policy") in {"quarantine", "review_required"}]
    if not sections_with_policy:
        return  # no suspicious section on this run
    target = sections_with_policy[0]
    linked = [e for e in evidence if e.get("section_id") == target["section_id"]]
    if not linked:
        return  # no evidence linked to target section
    for ev in linked:
        assert ev["evidence_policy"] == target["evidence_policy"], (
            f"evidence_type={ev.get('evidence_type')} evidence_policy mismatch: "
            f"expected {target['evidence_policy']!r}, got {ev.get('evidence_policy')!r}"
        )
        assert ev["section_quality_score"] == target["section_quality_score"], (
            f"evidence_type={ev.get('evidence_type')} section_quality_score mismatch"
        )
        assert ev["section_is_suspicious"] is True
