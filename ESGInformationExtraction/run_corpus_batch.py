#!/usr/bin/env python
"""
run_corpus_batch.py
===================
Batch runner: processes every document in a corpus directory using the
ESGInformationExtraction pipeline and produces a consolidated summary.

Usage:
  python run_corpus_batch.py --corpus-dir <dir> --output-dir <dir>
  python run_corpus_batch.py --corpus-dir <dir> --output-dir <dir> --doc-type 02_sustainability_statement_csrd_esrs
  python run_corpus_batch.py --corpus-dir <dir> --output-dir <dir> --dry-run

Discovery:
  Scans for manifest.json files under <corpus-dir>. Each manifest is one document.
  Uses manifest metadata (company_name, company_slug, fiscal_year, official_doc_type)
  to build the CLI command for run_pdf_extraction.py.

Output:
  - One sub-directory per document under <output-dir>/<document_id>/
  - batch_summary.json: aggregate stats across all processed documents
  - batch_recall_report.json: aggregate recall metrics (if recall_eval is available)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _discover_documents(
    corpus_dir: Path,
    doc_type_filter: str | None,
) -> list[dict]:
    """Return list of document specs from manifest.json files."""
    docs = []
    for manifest_path in sorted(corpus_dir.rglob("manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        doc_type = manifest.get("official_doc_type", "")
        if doc_type_filter and doc_type != doc_type_filter:
            continue

        company_slug = manifest.get("company_slug", "")
        fiscal_year  = manifest.get("fiscal_year", "")
        company_name = manifest.get("company_name", company_slug)

        if not company_slug or not fiscal_year:
            continue

        doc_id = f"{company_slug}_{fiscal_year}_{doc_type}".replace("-", "_")
        pdf_path = manifest_path.parent / "document.pdf"
        if not pdf_path.exists():
            continue

        docs.append({
            "document_id":    doc_id,
            "pdf_path":       str(pdf_path),
            "company":        company_name,
            "company_slug":   company_slug,
            "fiscal_year":    int(fiscal_year),
            "official_doc_type": doc_type,
            "manifest_path":  str(manifest_path),
        })

    return docs


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run_one(
    doc: dict,
    output_dir: Path,
    overwrite: bool = False,
    max_pages: int | None = None,
) -> dict:
    """Run pipeline on one document. Returns result dict."""
    doc_output_dir = output_dir / doc["document_id"]

    cli = [
        sys.executable, "-X", "utf8",
        str(PROJECT_ROOT / "ESGInformationExtraction" / "run_pdf_extraction.py"),
        "--pdf-path",    doc["pdf_path"],
        "--document-id", doc["document_id"],
        "--output-dir",  str(doc_output_dir),
        "--company",     doc["company"],
        "--company-slug", doc["company_slug"],
        "--fiscal-year", str(doc["fiscal_year"]),
    ]
    if overwrite:
        cli.append("--overwrite")
    if max_pages:
        cli.extend(["--max-pages", str(max_pages)])

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cli,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200,  # 2h max per document
        )
        elapsed = time.monotonic() - t0
        if result.returncode == 0:
            # Parse stdout JSON
            try:
                out_json = json.loads(result.stdout.strip().splitlines()[-1])
            except Exception:
                out_json = {"status": "success", "raw_stdout": result.stdout[-500:]}
            out_json["elapsed_s"] = round(elapsed, 1)
            out_json["returncode"] = 0
            return out_json
        else:
            return {
                "status": "failed",
                "returncode": result.returncode,
                "elapsed_s": round(elapsed, 1),
                "stderr": result.stderr[-1000:],
                "stdout": result.stdout[-500:],
            }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "elapsed_s": 7200, "returncode": -1}
    except Exception as e:
        return {"status": "error", "error": str(e), "elapsed_s": 0, "returncode": -1}


def _compute_batch_recall(output_dir: Path, docs: list[dict]) -> dict | None:
    """If recall_eval/compute_recall.py exists, run it on the output_dir."""
    recall_script = PROJECT_ROOT / "recall_eval" / "compute_recall.py"
    if not recall_script.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(recall_script), str(output_dir)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
        recall_json_path = output_dir / "recall_report.json"
        if recall_json_path.exists():
            return json.loads(recall_json_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ESG corpus batch runner")
    parser.add_argument("--corpus-dir",  required=True, help="Root of corpus (contains company sub-dirs)")
    parser.add_argument("--output-dir",  required=True, help="Where to write all document outputs")
    parser.add_argument("--doc-type",    default=None,  help="Filter by official_doc_type (e.g. 02_sustainability_statement_csrd_esrs)")
    parser.add_argument("--overwrite",   action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--max-pages",   type=int, default=None, help="Limit pages per document (for testing)")
    parser.add_argument("--dry-run",     action="store_true", help="Print what would run without executing")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    docs = _discover_documents(corpus_dir, args.doc_type)

    if not docs:
        print(f"No documents found in {corpus_dir}" +
              (f" with doc_type={args.doc_type!r}" if args.doc_type else ""))
        sys.exit(1)

    print(f"Discovered {len(docs)} documents:")
    for d in docs:
        print(f"  {d['document_id']}")
    print()

    if args.dry_run:
        print("DRY RUN — exiting without processing.")
        return

    results = []
    for i, doc in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] Processing {doc['document_id']} ...", flush=True)
        res = _run_one(doc, output_dir, overwrite=args.overwrite, max_pages=args.max_pages)
        res["document_id"] = doc["document_id"]
        res["company"] = doc["company"]
        res["fiscal_year"] = doc["fiscal_year"]
        res["doc_type"] = doc["official_doc_type"]
        results.append(res)
        status_icon = "✓" if res.get("status") == "success" else "✗"
        print(f"  {status_icon} status={res.get('status')} elapsed={res.get('elapsed_s', 0):.0f}s "
              f"pages={res.get('pages_processed', '?')} blocks={res.get('text_blocks_count', '?')}", flush=True)

    # Summary
    n_ok  = sum(1 for r in results if r.get("status") == "success")
    n_fail = len(results) - n_ok
    total_pages = sum(r.get("pages_processed", 0) for r in results)
    total_blocks = sum(r.get("text_blocks_count", 0) for r in results)

    print()
    print("=" * 60)
    print(f"BATCH COMPLETE: {n_ok}/{len(results)} success, {n_fail} failed")
    print(f"Total pages processed: {total_pages:,}")
    print(f"Total text blocks:     {total_blocks:,}")
    print("=" * 60)

    batch_summary = {
        "run_timestamp":     datetime.now(tz=timezone.utc).isoformat(),
        "corpus_dir":        str(corpus_dir),
        "output_dir":        str(output_dir),
        "doc_type_filter":   args.doc_type,
        "documents_total":   len(results),
        "documents_success": n_ok,
        "documents_failed":  n_fail,
        "total_pages":       total_pages,
        "total_blocks":      total_blocks,
        "results":           results,
    }

    summary_path = output_dir / "batch_summary.json"
    summary_path.write_text(
        json.dumps(batch_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nBatch summary written: {summary_path}")

    # If only one document, try recall evaluation
    if n_ok >= 1:
        print("\nRunning recall evaluation...", flush=True)
        recall = _compute_batch_recall(output_dir, docs)
        if recall:
            print(f"Recall: metric={recall.get('recall_metric_level', '?'):.1%}  "
                  f"value={recall.get('recall_value_level', '?'):.1%}  "
                  f"current_year={recall.get('recall_current_year_level', '?'):.1%}")
            print(f"Precision proxy: carry_value={recall.get('precision_proxy_carry_value', '?'):.1%}  "
                  f"noise={recall.get('precision_proxy_noise_ratio', '?'):.1%}")


if __name__ == "__main__":
    main()
