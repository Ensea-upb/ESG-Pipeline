"""
audit_selected_documents.py
============================
Audit qualite post-selection des documents ESG selectionnes.

REGLES D'USAGE DU CORPUS
--------------------------
  ESGFinalCorpus brut
      Ne pas utiliser directement pour l'extraction ESG.
      Il contient des documents non valides, mal attribues ou hors perimetre
      qui fausseraient les indicateurs extraits.

  extraction_index_strict_likely_valid.csv  (corpus strict)
      Utiliser pour toute extraction ESG stricte ou pour un benchmark.
      Ne contient que les documents classes KEEP_LIKELY_VALID.
      Garantit le meilleur signal/bruit possible.

  extraction_index_usable_excluding_quarantine.csv  (corpus large securise)
      Utiliser pour une extraction large mais securisee.
      Exclut les documents en QUARANTINE_LIKELY_WRONG_COMPANY.
      Inclut KEEP + REVIEW_STANDARD + REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED.

  exclusion_index_quarantine_wrong_company.csv  (liste noire)
      Documents a EXCLURE de toute extraction ESG sans exception.
      Ces documents ont ete detectes comme appartenant probablement
      a une mauvaise entreprise ou a une mauvaise periode.
      Ne pas les utiliser, meme pour des tests ou du prototypage.

PRINCIPE D'ISOLATION
---------------------
  Ce script est READ-ONLY sur ESGFinalCorpus et sur tous les fichiers d'entree.
  Il ne supprime, ne deplace, ne modifie aucun fichier PDF ni aucun manifest.
  Il ecrit uniquement dans le dossier de sortie passe en argument (--output-dir).
  Il n'est pas branche automatiquement dans ESGOrchestrator.

USAGE
-----
  python DocumentPostProcessing/scripts/audit_selected_documents.py

  Options :
    --selected-path    Chemin vers selected_documents.csv
                       (defaut : DocumentPostProcessing/data/selection/selected_documents.csv)
    --validation-path  Chemin vers document_validation_results.csv
                       (defaut : DocumentPostProcessing/data/validation/document_validation_results.csv)
    --output-dir       Dossier de sortie
                       (defaut : DocumentPostProcessing/data/quality_audit_v2)
    --overwrite        Requis pour ecraser un dossier de sortie existant

  Exemples :
    # Corpus local par defaut
    python DocumentPostProcessing/scripts/audit_selected_documents.py --overwrite

    # Run Onyxia ou run alternatif
    python DocumentPostProcessing/scripts/audit_selected_documents.py \\
      --selected-path  /runs/onyxia_pilot/postprocessing/selection/selected_documents.csv \\
      --validation-path /runs/onyxia_pilot/postprocessing/validation/document_validation_results.csv \\
      --output-dir     /runs/onyxia_pilot/postprocessing/quality_audit_v2 \\
      --overwrite
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Constantes ────────────────────────────────────────────────────────────────

AUDIT_BUCKET_PRIORITY: dict[str, int] = {
    "QUARANTINE_LIKELY_WRONG_COMPANY":           1,
    "REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED": 2,
    "REVIEW_STANDARD":                           3,
    "KEEP_LIKELY_VALID":                         4,
    "REVIEW_UNCLASSIFIED":                       5,
}

# Ordre de severite pour deduplication validation (le plus mauvais gagne)
_VALIDATION_SEVERITY: dict[str, int] = {
    "likely_wrong_company": 0,
    "needs_review":         1,
    "likely_valid":         2,
}


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    """Lit un CSV avec BOM optionnel. Leve FileNotFoundError si absent."""
    if not path.exists():
        raise FileNotFoundError(f"Fichier CSV introuvable : {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def _parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "oui")
    return False


# ── Logique de deduplication validation ──────────────────────────────────────

def _deduplicate_validation(
    validation_rows: list[dict],
) -> dict[tuple, dict]:
    """
    Reduit validation a une ligne par (canonical_document_id, company_slug, fiscal_year).
    En cas de conflit, retient le statut le plus defavorable.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in validation_rows:
        key = (
            row.get("canonical_document_id", "").strip(),
            row.get("company_slug", "").strip(),
            str(row.get("fiscal_year", "")).strip(),
        )
        groups[key].append(row)

    deduped: dict[tuple, dict] = {}
    for key, rows in groups.items():
        # Trie par severite croissante (0 = le pire), prend le premier
        rows_sorted = sorted(
            rows,
            key=lambda r: _VALIDATION_SEVERITY.get(
                r.get("document_validation_status", "").strip(), 99
            ),
        )
        deduped[key] = rows_sorted[0]
    return deduped


# ── Classification audit ──────────────────────────────────────────────────────

def _classify(row: dict) -> str:
    """
    Attribue un audit_bucket a partir des colonnes du document selectionne
    enrichi par la jointure validation.

    Ordre de priorite (du plus grave au moins grave) :
      1. QUARANTINE_LIKELY_WRONG_COMPANY
      2. REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED
      3. REVIEW_STANDARD
      4. KEEP_LIKELY_VALID
      5. REVIEW_UNCLASSIFIED
    """
    val_status    = row.get("_val_document_validation_status", "").strip().lower()
    sel_status    = row.get("selection_status", "").strip().lower()
    company_found = _parse_bool(row.get("company_name_detected_in_text", "False"))

    if val_status == "likely_wrong_company":
        return "QUARANTINE_LIKELY_WRONG_COMPANY"

    if val_status == "likely_valid" and sel_status == "selected":
        return "KEEP_LIKELY_VALID"

    if sel_status == "selected_needs_review" and not company_found:
        return "REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED"

    if sel_status == "selected_needs_review":
        return "REVIEW_STANDARD"

    # selected + val_status not likely_valid and not likely_wrong_company
    if sel_status == "selected" and val_status in ("needs_review", ""):
        return "REVIEW_STANDARD"

    return "REVIEW_UNCLASSIFIED"


# ── Verification des garde-fous ───────────────────────────────────────────────

def _guard_no_duplicates(audit_rows: list[dict], selected_rows: list[dict]) -> None:
    if len(audit_rows) != len(selected_rows):
        raise RuntimeError(
            f"GARDE-FOU : la jointure a produit {len(audit_rows)} lignes "
            f"alors que selected_documents en contient {len(selected_rows)}. "
            f"Verifier la cle de jointure et la deduplication validation."
        )
    # Verifier unicite par (company_slug, fiscal_year, official_doc_type)
    seen: set[tuple] = set()
    for row in audit_rows:
        key = (
            row.get("company_slug", ""),
            row.get("fiscal_year", ""),
            row.get("official_doc_type", ""),
        )
        if key in seen:
            raise RuntimeError(
                f"GARDE-FOU : doublon detecte apres jointure pour la cle {key}. "
                f"La deduplication validation est insuffisante."
            )
        seen.add(key)


# ── Construction de l'index d'extraction ─────────────────────────────────────

_EXTRACTION_INDEX_COLS = [
    "company_name",
    "company_slug",
    "fiscal_year",
    "official_doc_type",
    "official_doc_type_label",
    "selected_canonical_document_id",
    "sha256",
    "final_path",
    "final_file_exists",
    "page_count",
    "audit_bucket",
    "audit_priority",
    "validation_status_merged",
    "selection_status",
    "company_name_detected_in_text",
]


# ── Affichage resume ──────────────────────────────────────────────────────────

def _print_summary(
    selected_rows: list[dict],
    audit_rows: list[dict],
    output_dir: Path,
) -> None:
    sep = "=" * 68

    print(f"\n{sep}")
    print("  AUDIT QUALITE v2 — RESUME")
    print(sep)

    n_total      = len(audit_rows)
    n_keep       = sum(1 for r in audit_rows if r["audit_bucket"] == "KEEP_LIKELY_VALID")
    n_usable     = sum(1 for r in audit_rows if r["audit_bucket"] != "QUARANTINE_LIKELY_WRONG_COMPANY")
    n_quarantine = sum(1 for r in audit_rows if r["audit_bucket"] == "QUARANTINE_LIKELY_WRONG_COMPANY")
    n_existing   = sum(1 for r in audit_rows if r.get("final_file_exists") == "True")

    print(f"  Documents selectionnes en entree : {len(selected_rows)}")
    print(f"  Lignes audit produites           : {n_total}")
    print(f"  Fichiers PDF existants           : {n_existing}/{n_total}")
    print()
    print(f"  Corpus strict  (KEEP_LIKELY_VALID)              : {n_keep:>3} documents")
    print(f"  Corpus large   (hors quarantaine)               : {n_usable:>3} documents")
    print(f"  Quarantaine    (QUARANTINE_LIKELY_WRONG_COMPANY) : {n_quarantine:>3} documents")

    # Distribution complete audit_bucket
    bucket_counts: dict[str, int] = dict(Counter(r["audit_bucket"] for r in audit_rows))
    print(f"\n  Distribution audit_bucket :")
    for bucket in sorted(bucket_counts, key=lambda b: AUDIT_BUCKET_PRIORITY.get(b, 99)):
        prio = AUDIT_BUCKET_PRIORITY.get(bucket, 99)
        bar = "#" * bucket_counts[bucket]
        print(f"    [{prio}] {bucket:<50} : {bucket_counts[bucket]:>3}  {bar}")

    # Par company_name
    company_buckets: dict[str, list[str]] = defaultdict(list)
    for r in audit_rows:
        company_buckets[r.get("company_name", "?")].append(r["audit_bucket"])
    print(f"\n  Audit par entreprise :")
    for company in sorted(company_buckets):
        buckets = company_buckets[company]
        parts = []
        for b in sorted(set(buckets), key=lambda b: AUDIT_BUCKET_PRIORITY.get(b, 99)):
            short = b.replace("QUARANTINE_LIKELY_WRONG_COMPANY", "QUARANTINE") \
                     .replace("REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED", "REVIEW_HIGH") \
                     .replace("REVIEW_STANDARD", "REVIEW_STD") \
                     .replace("KEEP_LIKELY_VALID", "KEEP") \
                     .replace("REVIEW_UNCLASSIFIED", "REVIEW_UNK")
            parts.append(f"{short}={buckets.count(b)}")
        print(f"    {company:<30} : {', '.join(parts)}")

    # Par official_doc_type
    dtype_buckets: dict[str, list[str]] = defaultdict(list)
    for r in audit_rows:
        dtype_buckets[r.get("official_doc_type", "?")].append(r["audit_bucket"])
    print(f"\n  Audit par type documentaire :")
    for dt in sorted(dtype_buckets):
        buckets   = dtype_buckets[dt]
        keep      = buckets.count("KEEP_LIKELY_VALID")
        review    = sum(1 for b in buckets if b.startswith("REVIEW"))
        quarant   = buckets.count("QUARANTINE_LIKELY_WRONG_COMPANY")
        print(f"    {dt:<47} KEEP={keep}  REVIEW={review}  QUARANTINE={quarant}")

    # Index d'extraction
    print(f"\n  Index d'extraction :")
    print(f"    extraction_index_strict_likely_valid.csv         -> {n_keep:>3} docs  (corpus strict)")
    print(f"    extraction_index_usable_excluding_quarantine.csv -> {n_usable:>3} docs  (corpus large)")
    print(f"    exclusion_index_quarantine_wrong_company.csv     -> {n_quarantine:>3} docs  (liste noire)")

    # Fichiers produits
    print(f"\n  Tous les fichiers produits dans : {output_dir}")
    for f in sorted(output_dir.iterdir()):
        if f.suffix == ".csv":
            with f.open(encoding="utf-8") as fh:
                n = sum(1 for _ in fh) - 1
            print(f"    {f.name:<57} : {n:>3} lignes")
        elif f.suffix == ".json":
            print(f"    {f.name}")
    print(f"\n{sep}\n")


def _bucket_count(rows: list[dict], bucket: str) -> int:
    return sum(1 for row in rows if row.get("audit_bucket") == bucket)


def _build_group_summary(rows: list[dict], group_field: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(group_field, "") or "UNKNOWN")].append(row)

    summary_rows = []
    for key, items in sorted(grouped.items()):
        total = len(items)
        keep = _bucket_count(items, "KEEP_LIKELY_VALID")
        review_standard = _bucket_count(items, "REVIEW_STANDARD")
        review_high = _bucket_count(items, "REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED")
        quarantine = _bucket_count(items, "QUARANTINE_LIKELY_WRONG_COMPANY")
        summary_rows.append(
            {
                group_field: key,
                "total_selected": total,
                "keep_likely_valid": keep,
                "review_standard": review_standard,
                "review_high_priority_company_not_detected": review_high,
                "quarantine_likely_wrong_company": quarantine,
                "strict_valid_ratio": f"{(keep / total):.4f}" if total else "0.0000",
                "usable_excluding_quarantine": total - quarantine,
                "missing_final_path_count": sum(
                    1 for row in items if row.get("final_file_exists") != "True"
                ),
            }
        )
    return summary_rows


def _markdown_table(headers: list[str], rows: list[dict], max_rows: int = 20) -> str:
    if not rows:
        return "_No rows._"
    visible_rows = rows[:max_rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in visible_rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    if len(rows) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(rows)} rows._")
    return "\n".join(lines)


def _write_quality_report(
    output_dir: Path,
    audit_rows: list[dict],
    company_summary: list[dict],
    doc_type_summary: list[dict],
) -> None:
    total = len(audit_rows)
    keep = _bucket_count(audit_rows, "KEEP_LIKELY_VALID")
    review_standard = _bucket_count(audit_rows, "REVIEW_STANDARD")
    review_high = _bucket_count(audit_rows, "REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED")
    quarantine = _bucket_count(audit_rows, "QUARANTINE_LIKELY_WRONG_COMPANY")
    usable = total - quarantine
    missing_paths = sum(1 for row in audit_rows if row.get("final_file_exists") != "True")

    fragile_companies = sorted(
        company_summary,
        key=lambda row: (int(row["keep_likely_valid"]), -int(row["total_selected"]), row["company_name"]),
    )
    fragile_doc_types = sorted(
        doc_type_summary,
        key=lambda row: (
            -int(row["quarantine_likely_wrong_company"]) - int(row["review_high_priority_company_not_detected"]),
            int(row["keep_likely_valid"]),
            row["official_doc_type"],
        ),
    )

    lines = [
        "# Quality Audit V2",
        "",
        "Do not use raw ESGFinalCorpus directly for ESG extraction.",
        "",
        "Use `extraction_index_strict_likely_valid.csv` for first controlled extraction tests.",
        "Use `extraction_index_usable_excluding_quarantine.csv` only after strict extraction validation.",
        "`exclusion_index_quarantine_wrong_company.csv` is a deny-list and must be excluded.",
        "",
        "## Summary",
        "",
        f"- total_selected: {total}",
        f"- KEEP_LIKELY_VALID: {keep}",
        f"- REVIEW_STANDARD: {review_standard}",
        f"- REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED: {review_high}",
        f"- QUARANTINE_LIKELY_WRONG_COMPANY: {quarantine}",
        f"- strict_corpus_documents: {keep}",
        f"- usable_excluding_quarantine: {usable}",
        f"- missing_final_path_count: {missing_paths}",
        "",
        "## Most Fragile Companies",
        "",
        _markdown_table(
            [
                "company_name",
                "total_selected",
                "keep_likely_valid",
                "review_standard",
                "review_high_priority_company_not_detected",
                "quarantine_likely_wrong_company",
            ],
            fragile_companies,
            max_rows=15,
        ),
        "",
        "## Most Fragile Document Types",
        "",
        _markdown_table(
            [
                "official_doc_type",
                "total_selected",
                "keep_likely_valid",
                "review_standard",
                "review_high_priority_company_not_detected",
                "quarantine_likely_wrong_company",
            ],
            fragile_doc_types,
            max_rows=15,
        ),
        "",
        "## Output Indexes",
        "",
        f"- extraction_index_strict_likely_valid.csv: {_count_csv_rows(output_dir / 'extraction_index_strict_likely_valid.csv')}",
        f"- extraction_index_usable_excluding_quarantine.csv: {_count_csv_rows(output_dir / 'extraction_index_usable_excluding_quarantine.csv')}",
        f"- exclusion_index_quarantine_wrong_company.csv: {_count_csv_rows(output_dir / 'exclusion_index_quarantine_wrong_company.csv')}",
    ]
    (output_dir / "quality_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Point d'entree ────────────────────────────────────────────────────────────

def main(
    selected_path: Path,
    validation_path: Path,
    output_dir: Path,
    overwrite: bool,
) -> None:
    # ── Garde-fous sortie ────────────────────────────────────────────────────
    if output_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Le dossier de sortie existe deja : {output_dir}\n"
            f"Utiliser --overwrite pour l'ecraser."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Chargement ───────────────────────────────────────────────────────────
    print(f"Chargement selected_documents  : {selected_path}")
    selected_rows = _read_csv(selected_path)
    print(f"  -> {len(selected_rows)} documents selectionnes")

    print(f"Chargement validation_results  : {validation_path}")
    validation_rows = _read_csv(validation_path)
    print(f"  -> {len(validation_rows)} lignes validation brutes")

    # ── Deduplication validation ──────────────────────────────────────────────
    val_deduped = _deduplicate_validation(validation_rows)
    print(f"  -> {len(val_deduped)} entrees validation apres deduplication")

    # ── Jointure ─────────────────────────────────────────────────────────────
    audit_rows: list[dict] = []
    unmatched = 0

    for sel in selected_rows:
        can_id     = sel.get("selected_canonical_document_id", "").strip()
        slug       = sel.get("company_slug", "").strip()
        fiscal_yr  = str(sel.get("fiscal_year", "")).strip()

        val_key = (can_id, slug, fiscal_yr)
        val_row = val_deduped.get(val_key)

        if val_row is None:
            # Tentative sans fiscal_year (parfois absent dans validation)
            for k, v in val_deduped.items():
                if k[0] == can_id and k[1] == slug:
                    val_row = v
                    break

        if val_row is None:
            unmatched += 1

        # Valeur de validation_status fusionnee
        val_doc_status = (
            val_row.get("document_validation_status", "").strip()
            if val_row else sel.get("validation_status", "").strip()
        )

        # company_name_detected : priorite selected, fallback validation
        company_detected = sel.get("company_name_detected_in_text", "")
        if company_detected == "" and val_row:
            company_detected = val_row.get("company_name_detected_in_text", "False")

        merged = dict(sel)
        merged["_val_document_validation_status"] = val_doc_status
        merged["company_name_detected_in_text"]   = company_detected
        merged["validation_status_merged"]        = val_doc_status

        # Champs supplementaires depuis validation
        if val_row:
            merged["probable_language"]          = val_row.get("probable_language", "")
            merged["technical_validation_status"] = val_row.get("technical_validation_status", "")
            merged["validation_notes"]            = val_row.get("validation_notes", "")
            merged["is_pdf_header_valid"]         = val_row.get("is_pdf_header_valid", "")
            merged["file_size_mb"]               = val_row.get("file_size_mb", "")
        else:
            merged["probable_language"]           = ""
            merged["technical_validation_status"] = ""
            merged["validation_notes"]            = ""
            merged["is_pdf_header_valid"]         = ""
            merged["file_size_mb"]               = ""

        # Classification
        merged["audit_bucket"]   = _classify(merged)
        merged["audit_priority"] = AUDIT_BUCKET_PRIORITY.get(merged["audit_bucket"], 5)

        # Existence fichier final
        final_path = merged.get("final_path", "").strip()
        merged["final_file_exists"] = str(Path(final_path).exists()) if final_path else "False"

        # Nettoyage cle interne
        del merged["_val_document_validation_status"]

        audit_rows.append(merged)

    if unmatched > 0:
        print(
            f"  [WARN] {unmatched} document(s) selectionne(s) sans correspondance "
            f"dans validation — statut fallback depuis selected_documents.csv"
        )

    # ── Garde-fous jointure ───────────────────────────────────────────────────
    _guard_no_duplicates(audit_rows, selected_rows)

    # ── Colonnes output ───────────────────────────────────────────────────────
    base_cols = list(selected_rows[0].keys())
    extra_cols = [
        "validation_status_merged",
        "audit_bucket",
        "audit_priority",
        "final_file_exists",
        "probable_language",
        "technical_validation_status",
        "is_pdf_header_valid",
        "file_size_mb",
        "validation_notes",
    ]
    all_cols = base_cols + [c for c in extra_cols if c not in base_cols]

    # ── Fichier principal ─────────────────────────────────────────────────────
    audit_sorted = sorted(audit_rows, key=lambda r: (r["audit_priority"], r.get("company_name", "")))
    _write_csv(
        output_dir / "selected_documents_quality_audit_v2.csv",
        audit_sorted,
        all_cols,
    )

    # ── Sous-ensembles ────────────────────────────────────────────────────────
    quarantine = [r for r in audit_rows if r["audit_bucket"] == "QUARANTINE_LIKELY_WRONG_COMPANY"]
    clean      = [r for r in audit_rows if r["audit_bucket"] == "KEEP_LIKELY_VALID"]
    review     = [r for r in audit_rows if r["audit_bucket"].startswith("REVIEW")]

    _write_csv(output_dir / "selected_documents_quarantine_v2.csv",      quarantine, all_cols)
    _write_csv(output_dir / "selected_documents_clean_likely_valid_v2.csv", clean,   all_cols)
    _write_csv(output_dir / "selected_documents_to_review_v2.csv",       review,    all_cols)

    # ── Index d'extraction ────────────────────────────────────────────────────
    ext_cols_present = [c for c in _EXTRACTION_INDEX_COLS if c in all_cols or c in (extra_cols)]

    strict = [r for r in audit_rows if r["audit_bucket"] == "KEEP_LIKELY_VALID"]
    usable = [r for r in audit_rows if r["audit_bucket"] != "QUARANTINE_LIKELY_WRONG_COMPANY"]
    excluded = quarantine

    _write_csv(output_dir / "extraction_index_strict_likely_valid.csv",      strict,  ext_cols_present)
    _write_csv(output_dir / "extraction_index_usable_excluding_quarantine.csv", usable, ext_cols_present)
    _write_csv(output_dir / "exclusion_index_quarantine_wrong_company.csv",  excluded, ext_cols_present)

    company_summary = _build_group_summary(audit_rows, "company_name")
    doc_type_summary = _build_group_summary(audit_rows, "official_doc_type")
    summary_cols = [
        "total_selected",
        "keep_likely_valid",
        "review_standard",
        "review_high_priority_company_not_detected",
        "quarantine_likely_wrong_company",
        "strict_valid_ratio",
        "usable_excluding_quarantine",
        "missing_final_path_count",
    ]
    _write_csv(
        output_dir / "quality_summary_by_company.csv",
        company_summary,
        ["company_name", *summary_cols],
    )
    _write_csv(
        output_dir / "quality_summary_by_doc_type.csv",
        doc_type_summary,
        ["official_doc_type", *summary_cols],
    )
    _write_quality_report(output_dir, audit_rows, company_summary, doc_type_summary)

    # ── Metadonnees JSON ──────────────────────────────────────────────────────
    summary = {
        "run_inputs": {
            "selected_path":   str(selected_path),
            "validation_path": str(validation_path),
        },
        "counts": {
            "selected_documents":       len(selected_rows),
            "validation_rows_raw":      len(validation_rows),
            "validation_rows_deduped":  len(val_deduped),
            "audit_rows":               len(audit_rows),
            "unmatched_in_validation":  unmatched,
        },
        "audit_bucket_distribution": dict(
            Counter(r["audit_bucket"] for r in audit_rows)
        ),
        "final_file_exists": {
            "true":  sum(1 for r in audit_rows if r["final_file_exists"] == "True"),
            "false": sum(1 for r in audit_rows if r["final_file_exists"] != "True"),
        },
        "output_files": {
            "selected_documents_quality_audit_v2.csv":         len(audit_rows),
            "selected_documents_quarantine_v2.csv":            len(quarantine),
            "selected_documents_clean_likely_valid_v2.csv":    len(clean),
            "selected_documents_to_review_v2.csv":             len(review),
            "extraction_index_strict_likely_valid.csv":        len(strict),
            "extraction_index_usable_excluding_quarantine.csv": len(usable),
            "exclusion_index_quarantine_wrong_company.csv":    len(excluded),
            "quality_summary_by_company.csv":                  len(company_summary),
            "quality_summary_by_doc_type.csv":                 len(doc_type_summary),
            "quality_audit_report.md":                         1,
        },
    }
    with (output_dir / "audit_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ── Resume console ────────────────────────────────────────────────────────
    _print_summary(selected_rows, audit_rows, output_dir)


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    dp_data = repo_root / "DocumentPostProcessing" / "data"
    env_output_root = (
        Path(os.environ["ESG_POSTPROCESS_OUTPUT_ROOT"])
        if "ESG_POSTPROCESS_OUTPUT_ROOT" in os.environ
        else None
    )
    default_selected = (
        env_output_root / "selection" / "selected_documents.csv"
        if env_output_root
        else dp_data / "selection" / "selected_documents.csv"
    )
    default_validation = (
        env_output_root / "validation" / "document_validation_results.csv"
        if env_output_root
        else dp_data / "validation" / "document_validation_results.csv"
    )
    default_output_dir = (
        env_output_root / "quality_audit_v2"
        if env_output_root
        else dp_data / "quality_audit_v2"
    )

    parser = argparse.ArgumentParser(
        description="Audit qualite v2 des documents ESG selectionnes."
    )
    parser.add_argument(
        "--selected-path",
        type=Path,
        default=default_selected,
        help="Chemin vers selected_documents.csv",
    )
    parser.add_argument(
        "--validation-path",
        type=Path,
        default=default_validation,
        help="Chemin vers document_validation_results.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Dossier de sortie (cree si absent)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Ecraser le dossier de sortie si existant",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main(
        selected_path=args.selected_path,
        validation_path=args.validation_path,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
