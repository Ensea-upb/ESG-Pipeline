"""
run_extraction_test.py
======================
LEGACY WARNING:
This script belongs to an older experimental ESGInformationExtraction chain.
For ESGInformationExtraction v1.x, use ESGInformationExtraction/run_pdf_extraction.py
and the documented v1.x validation CLIs instead.

Test end-to-end du pipeline ESGInformationExtraction sur le corpus existant.
Ne touche jamais au corpus source.

Usage :
    python run_extraction_test.py
    python run_extraction_test.py --company lvmh
    python run_extraction_test.py --limit 3
"""

from __future__ import annotations

import sys
import argparse
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

CORPUS_PATH = REPO_ROOT / "ESGFinalCorpus"
OUTPUT_ROOT = REPO_ROOT / "ESGInformationExtraction" / "outputs"

from ESGInformationExtraction.document_base.build_document_base import scan_corpus, write_document_base
from ESGInformationExtraction.parsing.pdf_text_parser import parse_pdf_pages
from ESGInformationExtraction.parsing.page_index_builder import build_page_records, write_page_index
from ESGInformationExtraction.section_detection.heading_detector import detect_headings
from ESGInformationExtraction.section_detection.section_index_builder import build_section_records, write_section_index
from ESGInformationExtraction.extraction.metric_candidate_extractor import extract_metric_candidates
from ESGInformationExtraction.evidence.evidence_store import build_evidence_records, write_evidence_store
from ESGInformationExtraction.quality_control.quality_checks import (
    check_document_path_exists,
    check_empty_text,
    check_missing_evidence,
    write_quality_report,
)


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main(company_filter: str | None, limit: int | None) -> None:
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run ID : {run_id}")
    print(f"Output : {output_dir}")

    # ── 1. Scan du corpus ───────────────────────────────────────────
    separator("1. Scan du corpus")
    documents = scan_corpus(CORPUS_PATH)
    print(f"Documents trouves : {len(documents)}")

    if company_filter:
        documents = [d for d in documents if company_filter.lower() in d.company_slug.lower()]
        print(f"Apres filtre '{company_filter}' : {len(documents)}")

    if limit:
        documents = documents[:limit]
        print(f"Limite appliquee : {len(documents)} document(s)")

    if not documents:
        print("Aucun document a traiter.")
        return

    write_document_base(documents, output_dir)
    print(f"document_base.jsonl ecrit ({len(documents)} lignes)")

    # ── 2. Pipeline par document ────────────────────────────────────
    all_quality_checks = []
    total_pages = 0
    total_sections = 0
    total_evidence = 0

    for doc in documents:
        separator(f"2. Document : {doc.company_slug} / {doc.fiscal_year} / {doc.official_doc_type}")
        print(f"   PDF : {doc.document_path}")

        # QC : existence du PDF
        qc_path = check_document_path_exists(doc)
        all_quality_checks.append(qc_path)
        if qc_path.status == "fail":
            print(f"   [FAIL] PDF introuvable — document ignore.")
            continue
        print(f"   [OK] PDF present")

        # ── Parsing ──────────────────────────────────────────────────
        try:
            raw_pages = parse_pdf_pages(Path(doc.document_path))
        except ImportError as e:
            print(f"   [SKIP] {e}")
            continue
        except Exception as e:
            print(f"   [ERROR] Parsing echoue : {e}")
            continue

        page_records = build_page_records(doc, raw_pages)
        write_page_index(page_records, output_dir)
        total_pages += len(page_records)

        empty_pages = [p for p in page_records if p.extraction_status == "empty"]
        print(f"   Pages : {len(page_records)} total, {len(empty_pages)} vides")
        for page in page_records:
            qc = check_empty_text(page)
            if qc.status != "pass":
                all_quality_checks.append(qc)

        # ── Detection de sections ─────────────────────────────────────
        section_candidates = detect_headings(raw_pages)
        section_records = build_section_records(doc, section_candidates)
        write_section_index(section_records, output_dir)
        total_sections += len(section_records)
        print(f"   Sections detectees : {len(section_records)}")

        if section_records:
            for sr in section_records[:5]:
                print(f"     p.{sr.page_start:>3}  [{sr.section_type:<20}]  {sr.section_title[:60]}")
            if len(section_records) > 5:
                print(f"     ... et {len(section_records) - 5} de plus")

        # ── Extraction de candidats metriques ─────────────────────────
        metric_candidates = extract_metric_candidates(raw_pages)
        evidence_records = build_evidence_records(doc, metric_candidates, section_records)
        write_evidence_store(evidence_records, output_dir)
        total_evidence += len(evidence_records)
        print(f"   Candidats metriques : {len(metric_candidates)}, evidences : {len(evidence_records)}")

        if metric_candidates:
            seen: set[str] = set()
            for mc in metric_candidates:
                mid = mc["metric_id"]
                if mid not in seen:
                    seen.add(mid)
                    print(f"     metric: {mid:<25}  val='{mc['raw_value']}'  unit='{mc['raw_unit']}'  p.{mc['page_number']}")
                    if len(seen) >= 8:
                        print(f"     ... ({len(metric_candidates) - len(seen)} autres)")
                        break

        # QC : evidence manquante
        qc_ev = check_missing_evidence(doc, evidence_records)
        all_quality_checks.append(qc_ev)
        if qc_ev.status != "pass":
            print(f"   [WARN] {qc_ev.message}")

    # ── 3. Rapport qualite ──────────────────────────────────────────
    separator("3. Rapport qualite")
    write_quality_report(all_quality_checks, output_dir)
    fails = [q for q in all_quality_checks if q.status == "fail"]
    warnings = [q for q in all_quality_checks if q.status == "warning"]
    print(f"Checks : {len(all_quality_checks)} total / {len(fails)} fail / {len(warnings)} warning")
    for q in fails:
        print(f"  [FAIL] {q.check_name} : {q.message}")

    # ── 4. Resume ───────────────────────────────────────────────────
    separator("4. Resume")
    print(f"Documents traites : {len(documents)}")
    print(f"Pages extraites   : {total_pages}")
    print(f"Sections          : {total_sections}")
    print(f"Evidences         : {total_evidence}")
    print(f"\nFichiers produits dans : {output_dir}")
    for f in sorted(output_dir.iterdir()):
        lines = sum(1 for _ in f.open(encoding="utf-8")) if f.suffix in (".jsonl", ".json") else "-"
        print(f"  {f.name:<30} {lines} lignes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test pipeline ESGInformationExtraction")
    parser.add_argument("--company", default=None, help="Filtrer par slug entreprise (ex: lvmh)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter au N premiers documents")
    args = parser.parse_args()
    main(company_filter=args.company, limit=args.limit)
