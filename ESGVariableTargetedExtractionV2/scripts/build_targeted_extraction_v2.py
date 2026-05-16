"""
build_targeted_extraction_v2.py — Main CLI for ESGVariableTargetedExtractionV2.

Usage:
    python ESGVariableTargetedExtractionV2/scripts/build_targeted_extraction_v2.py \\
        --input-dir "<ESGInformationExtraction output dir>" \\
        --output-dir "ESGVariableTargetedExtractionV2/outputs/<run_id>" \\
        --config "ESGVariableTargetedExtractionV2/config/extraction_v2_config.yaml" \\
        --variables all \\
        --embedding-backend lexical \\
        --overwrite
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.config import load_config
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.input_adapter import load_document_input
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.document_chunk_index import build_all_chunks
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import SemanticCatalog
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.embedding_backends import get_backend
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.hybrid_retriever import HybridRetriever
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.table_layout_rebuilder import TableLayoutRebuilder
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.visual_evidence_recovery import recover_visual_evidence
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.constrained_extractor import ConstrainedExtractor
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.candidate_scorer import CandidateScorer
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.output_adapter import OutputAdapter
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.validators import validate_candidates_against_contract


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ESGVariableTargetedExtractionV2 — build targeted candidates")
    p.add_argument("--input-dir", required=True, help="ESGInformationExtraction output directory")
    p.add_argument("--output-dir", required=True, help="Output directory for V2 results")
    p.add_argument("--config", default=None, help="Path to extraction_v2_config.yaml")
    p.add_argument("--variables", default="all",
                   help="Comma-separated list of target variables, or 'all'")
    p.add_argument("--embedding-backend", default="auto",
                   choices=["auto", "huggingface", "lexical", "fake"],
                   help="Embedding backend to use")
    p.add_argument("--top-k", type=int, default=None, help="Override top_k_per_variable")
    p.add_argument("--no-visual", action="store_true", help="Skip visual evidence recovery")
    p.add_argument("--no-tables", action="store_true", help="Skip table layout rebuilder")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    return p.parse_args()


def main() -> dict:
    args = parse_args()
    start = time.time()

    output_dir = Path(args.output_dir)
    if output_dir.exists() and not args.overwrite:
        sentinel = output_dir / "extraction_v2_summary.json"
        if sentinel.exists():
            print(json.dumps({
                "status": "skipped",
                "reason": "output_already_exists",
                "output_dir": str(output_dir),
            }))
            return {"status": "skipped"}

    # Load config
    cfg = load_config(args.config)
    if args.top_k:
        cfg.retrieval.top_k_per_variable = args.top_k
    if args.embedding_backend != "auto":
        cfg.embedding.backend = args.embedding_backend

    # Load catalog
    catalog = SemanticCatalog()
    if len(catalog) == 0:
        print(json.dumps({"status": "failed", "error": "Semantic catalog empty or not found"}))
        return {"status": "failed"}

    # Determine variables
    if args.variables == "all":
        variables = catalog.list_variables()
    else:
        variables = [v.strip() for v in args.variables.split(",") if v.strip()]
        unknown = [v for v in variables if v not in catalog]
        if unknown:
            print(json.dumps({"status": "failed", "error": f"Unknown variables: {unknown}"}))
            return {"status": "failed"}

    # Load document input
    doc_input = load_document_input(args.input_dir)
    if not doc_input.has_valid_metadata:
        print(json.dumps({
            "status": "failed",
            "error": "metadata_missing",
            "load_warnings": doc_input.load_warnings,
        }))
        return {"status": "failed"}

    # Build chunks
    chunks = build_all_chunks(doc_input)

    # Optionally run table layout rebuilder
    if not args.no_tables:
        rebuilder = TableLayoutRebuilder()
        table_ctx = rebuilder.rebuild(doc_input)
        # Convert table context to chunk format for retrieval
        for tc in table_ctx[:500]:
            if not tc.get("iso_standard_detected") and not tc.get("probable_footnote"):
                cell_text = tc.get("cell_text", "")
                row_h = tc.get("row_header", "")
                col_h = tc.get("col_header", "")
                unit = tc.get("nearby_unit", "")
                text = f"{cell_text} {row_h} {col_h} {unit}".strip()
                if text and len(text) > 3:
                    chunks.append({
                        "chunk_id": f"tbl_{tc.get('cell_id', '')}",
                        "document_id": doc_input.document_id,
                        "company": doc_input.company,
                        "company_name": doc_input.company_name,
                        "company_slug": doc_input.company_slug,
                        "fiscal_year": doc_input.fiscal_year,
                        "official_doc_type": doc_input.official_doc_type,
                        "final_path": doc_input.final_path,
                        "page_number": tc.get("page_number", ""),
                        "section_id": "",
                        "evidence_id": "",
                        "table_id": tc.get("table_id", ""),
                        "figure_id": "",
                        "crop_id": "",
                        "source_type": "table_cell_context",
                        "text": text,
                        "text_length": len(text),
                        "has_numeric_value": any(c.isdigit() for c in text),
                        "has_unit_candidate": bool(unit),
                        "numeric_values_detected": "",
                        "units_detected": unit,
                        "structural_noise_flags": ";".join(tc.get("warnings", "").split(";")[:2])
                        if tc.get("warnings") else "",
                    })

    # Visual evidence recovery
    if not args.no_visual:
        visual_findings = recover_visual_evidence(doc_input, Path(args.input_dir))
        # Add caption-based chunks
        for vf in visual_findings:
            detected = vf.get("detected_text", "")
            if detected and len(detected) > 10:
                chunks.append({
                    "chunk_id": f"vis_{vf.get('figure_id', vf.get('crop_id', ''))}",
                    "document_id": doc_input.document_id,
                    "company": doc_input.company,
                    "company_name": doc_input.company_name,
                    "company_slug": doc_input.company_slug,
                    "fiscal_year": doc_input.fiscal_year,
                    "official_doc_type": doc_input.official_doc_type,
                    "final_path": doc_input.final_path,
                    "page_number": vf.get("page_number", ""),
                    "section_id": "",
                    "evidence_id": "",
                    "table_id": "",
                    "figure_id": vf.get("figure_id", ""),
                    "crop_id": vf.get("crop_id", ""),
                    "source_type": "visual_crop_context",
                    "text": detected,
                    "text_length": len(detected),
                    "has_numeric_value": any(c.isdigit() for c in detected),
                    "has_unit_candidate": False,
                    "numeric_values_detected": "",
                    "units_detected": "",
                    "structural_noise_flags": "",
                })

    # Build embedding backend
    backend, backend_status = get_backend(
        backend_name=cfg.embedding.backend,
        model_name=cfg.embedding.model_name,
        local_model_path=cfg.embedding.local_model_path,
        device=cfg.embedding.device,
        batch_size=cfg.embedding.batch_size,
        normalize_embeddings=cfg.embedding.normalize_embeddings,
        offline_mode=cfg.embedding.offline_mode,
        fallback_backend=cfg.embedding.fallback_backend,
    )

    # Hybrid retrieval
    retriever = HybridRetriever(
        catalog=catalog,
        backend=backend,
        embedding_weight=cfg.retrieval.embedding_weight,
        keyword_weight=cfg.retrieval.keyword_weight,
        unit_weight=cfg.retrieval.unit_weight,
        section_weight=cfg.retrieval.section_weight,
        top_k=cfg.retrieval.top_k_per_variable,
        min_score=cfg.retrieval.min_retrieval_score,
    )
    retrieval_results = retriever.retrieve_all_variables(chunks, variables)

    # Constrained extraction
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    extractor = ConstrainedExtractor(
        catalog=catalog,
        schema_version=cfg.output.schema_version,
        reject_iso=cfg.extraction.reject_iso_standards_as_values,
        reject_section_numbers=cfg.extraction.reject_section_numbers_as_values,
        reject_page_numbers=cfg.extraction.reject_page_numbers_as_values,
        reject_footnotes=cfg.extraction.reject_footnotes_as_values,
    )
    candidates = extractor.extract_from_retrieval(retrieval_results, chunks_by_id)

    # Score candidates
    scorer = CandidateScorer(catalog)
    candidates = scorer.score_all(candidates)

    # Validate against contract
    contract_path = _ROOT / "ESGVariableTargetedExtractionV2" / "contracts" / "targeted_candidates_v2_contract.json"
    validation = validate_candidates_against_contract(candidates, contract_path if contract_path.exists() else None)

    # Write outputs
    elapsed = time.time() - start
    adapter = OutputAdapter(output_dir, cfg.output.schema_version)
    summary = adapter.write_all(
        doc_input=doc_input,
        chunks=chunks,
        retrieval_results=retrieval_results,
        candidates=candidates,
        embedding_backend_status=backend_status,
        variables_requested=variables,
        elapsed_seconds=elapsed,
    )
    adapter.write_contract_validation(validation)

    result = {
        "status": "success",
        "document_id": doc_input.document_id,
        "company": doc_input.company,
        "fiscal_year": doc_input.fiscal_year,
        "chunks_built": len(chunks),
        "retrieval_results": len(retrieval_results),
        "candidates_total": len(candidates),
        "candidates_found": summary.get("candidates_found", 0),
        "candidates_needs_review": summary.get("candidates_needs_review", 0),
        "variables_covered": summary.get("variables_covered_count", 0),
        "embedding_backend_status": backend_status,
        "elapsed_seconds": round(elapsed, 1),
        "output_dir": str(output_dir),
    }
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    main()
