#!/usr/bin/env python
"""Non-destructive audit for an ESGOrchestrator run directory.

The script reads existing run outputs and writes only:
- <run_dir>/audit_report.md
- <run_dir>/audit_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - pandas is optional by design
    pd = None


POSTPROCESSING_FILES = {
    "central_registry": ("documents_registry.csv",),
    "canonical_registry": ("canonical_documents.csv", "canonical_registry.csv"),
    "deduplication_summary": ("deduplication_summary.json",),
    "canonical_registry_summary": ("canonical_registry_summary.json",),
    "taxonomy_index": ("taxonomy_organized_documents_index.csv",),
    "validation_results": ("document_validation_results.csv",),
    "selection_results": ("selected_documents.csv",),
    "rejected_documents": ("rejected_documents.csv",),
    "selection_summary": ("document_selection_summary.json",),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_posix(path: Path) -> str:
    return path.as_posix()


def read_json(path: Path, alerts: list[dict[str, str]]) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        alerts.append(
            {
                "level": "CRITICAL",
                "message": f"JSON illisible: {path} ({type(exc).__name__}: {exc})",
            }
        )
        return None


def read_csv_records(path: Path, alerts: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        if pd is not None:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            return df.to_dict(orient="records")
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        alerts.append(
            {
                "level": "CRITICAL",
                "message": f"CSV illisible: {path} ({type(exc).__name__}: {exc})",
            }
        )
        return []


def find_first(root: Path, filename: str) -> Path | None:
    if not root.exists():
        return None
    direct = root / filename
    if direct.exists():
        return direct
    matches = sorted(root.rglob(filename))
    return matches[0] if matches else None


def find_first_of(root: Path, filenames: tuple[str, ...]) -> Path | None:
    for filename in filenames:
        match = find_first(root, filename)
        if match:
            return match
    return None


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob(pattern) if p.is_file())


def value_counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in records:
        value = str(row.get(key, "")).strip()
        if value:
            counter[value] += 1
    return dict(counter)


def table_from_counts(counts: dict[str, int], empty: str = "Aucune donnee.") -> str:
    if not counts:
        return empty
    lines = ["| Valeur | Nombre |", "|---|---:|"]
    for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {escape_md(key)} | {value} |")
    return "\n".join(lines)


def escape_md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def bool_text(value: bool) -> str:
    return "oui" if value else "non"


def path_exists_from_value(value: Any, run_dir: Path) -> bool | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.exists():
        return True
    if not path.is_absolute() and (run_dir / path).exists():
        return True
    return False


def first_present_key(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def collect_task_state(run_dir: Path, alerts: list[dict[str, str]]) -> dict[str, Any]:
    task_log_path = run_dir / "task_log.csv"
    run_state_path = run_dir / "run_state.json"
    final_summary_path = run_dir / "final_summary.json"
    coverage_path = run_dir / "coverage_matrix.csv"

    task_records = read_csv_records(task_log_path, alerts)
    run_state = read_json(run_state_path, alerts) if run_state_path.exists() else None
    final_summary = read_json(final_summary_path, alerts) if final_summary_path.exists() else None
    coverage_records = read_csv_records(coverage_path, alerts)

    if not final_summary_path.exists():
        alerts.append({"level": "CRITICAL", "message": "final_summary.json absent."})

    status_counts = value_counts(task_records, "status")
    if not status_counts and isinstance(final_summary, dict):
        raw_counts = final_summary.get("status_counts", {})
        if isinstance(raw_counts, dict):
            status_counts = {str(k): int(v) for k, v in raw_counts.items()}

    total_tasks = len(task_records)
    if not total_tasks and isinstance(final_summary, dict):
        try:
            total_tasks = int(final_summary.get("total_tasks", 0) or 0)
        except Exception:
            total_tasks = 0

    other_statuses = {
        key: value
        for key, value in status_counts.items()
        if key not in {"success", "failed", "skipped_not_applicable"}
    }

    return {
        "paths": {
            "task_log": as_posix(task_log_path),
            "run_state": as_posix(run_state_path),
            "final_summary": as_posix(final_summary_path),
            "coverage_matrix": as_posix(coverage_path),
        },
        "exists": {
            "task_log": task_log_path.exists(),
            "run_state": run_state_path.exists(),
            "final_summary": final_summary_path.exists(),
            "coverage_matrix": coverage_path.exists(),
        },
        "total_tasks": total_tasks,
        "status_counts": status_counts,
        "success": status_counts.get("success", 0),
        "failed": status_counts.get("failed", 0),
        "skipped_not_applicable": status_counts.get("skipped_not_applicable", 0),
        "other_statuses": other_statuses,
        "by_company": value_counts(task_records, "company_slug")
        or value_counts(coverage_records, "company_slug"),
        "by_year": value_counts(task_records, "fiscal_year")
        or value_counts(coverage_records, "fiscal_year"),
        "by_doc_type": value_counts(task_records, "official_doc_type")
        or value_counts(coverage_records, "official_doc_type"),
        "run_config": run_state.get("run_config", {}) if isinstance(run_state, dict) else {},
    }


def collect_postprocessing_state(
    run_dir: Path, alerts: list[dict[str, str]]
) -> dict[str, Any]:
    pp_dir = run_dir / "postprocessing"
    located = {key: find_first_of(pp_dir, filenames) for key, filenames in POSTPROCESSING_FILES.items()}

    central = read_csv_records(located["central_registry"], alerts) if located["central_registry"] else []
    canonical = (
        read_csv_records(located["canonical_registry"], alerts)
        if located["canonical_registry"]
        else []
    )
    taxonomy = read_csv_records(located["taxonomy_index"], alerts) if located["taxonomy_index"] else []
    validation = (
        read_csv_records(located["validation_results"], alerts)
        if located["validation_results"]
        else []
    )
    selected = (
        read_csv_records(located["selection_results"], alerts)
        if located["selection_results"]
        else []
    )
    rejected = (
        read_csv_records(located["rejected_documents"], alerts)
        if located["rejected_documents"]
        else []
    )

    dedup_summary = (
        read_json(located["deduplication_summary"], alerts)
        if located["deduplication_summary"]
        else None
    )
    canonical_summary = (
        read_json(located["canonical_registry_summary"], alerts)
        if located["canonical_registry_summary"]
        else None
    )
    selection_summary = (
        read_json(located["selection_summary"], alerts)
        if located["selection_summary"]
        else None
    )

    validation_status_counts = value_counts(validation, "document_validation_status")
    selection_status_counts = value_counts(selected, "selection_status")
    rejection_status_counts = value_counts(rejected, "rejection_status")

    return {
        "exists": {key: bool(path and path.exists()) for key, path in located.items()},
        "paths": {key: as_posix(path) if path else "" for key, path in located.items()},
        "central_documents": len(central),
        "unique_documents": len(canonical)
        or int((canonical_summary or {}).get("total_unique_documents", 0) or 0),
        "duplicate_groups": int(
            ((canonical_summary or {}).get("total_duplicate_groups"))
            or ((dedup_summary or {}).get("total_duplicate_groups"))
            or 0
        ),
        "validated_documents": len(validation),
        "selected_documents": len(selected),
        "rejected_documents": len(rejected),
        "needs_review": validation_status_counts.get("needs_review", 0)
        + rejection_status_counts.get("needs_review", 0),
        "likely_wrong_company": validation_status_counts.get("likely_wrong_company", 0)
        + rejection_status_counts.get("likely_wrong_company", 0),
        "selected_needs_review": selection_status_counts.get("selected_needs_review", 0),
        "taxonomy_status_counts": value_counts(taxonomy, "status"),
        "validation_status_counts": validation_status_counts,
        "selection_status_counts": selection_status_counts,
        "rejection_status_counts": rejection_status_counts,
        "records": {
            "selected": selected,
            "rejected": rejected,
            "taxonomy": taxonomy,
            "validation": validation,
        },
    }


def collect_physical_state(run_dir: Path) -> dict[str, Any]:
    dirs = {
        "postprocessing": run_dir / "postprocessing",
        "ESGCorpus": run_dir / "ESGCorpus",
        "ESGCorpusTaxonomy": run_dir / "ESGCorpusTaxonomy",
        "ESGFinalCorpus": run_dir / "ESGFinalCorpus",
    }
    return {
        "directories": {key: as_posix(path) for key, path in dirs.items()},
        "exists": {key: path.exists() for key, path in dirs.items()},
        "pdf_counts": {key: count_files(path, "*.pdf") for key, path in dirs.items()},
        "manifest_json": sum(count_files(path, "manifest.json") for path in dirs.values()),
        "references_json": sum(count_files(path, "references.json") for path in dirs.values()),
    }


def audit_final_corpus(
    run_dir: Path, selected_records: list[dict[str, Any]], alerts: list[dict[str, str]]
) -> dict[str, Any]:
    final_root = run_dir / "ESGFinalCorpus"
    issues: list[str] = []
    checked_dirs = 0
    complete_dirs = 0
    broken_final_paths = 0

    if not final_root.exists():
        alerts.append({"level": "CRITICAL", "message": "Dossier ESGFinalCorpus absent."})
        return {
            "checked_dirs": 0,
            "complete_dirs": 0,
            "missing_components": [],
            "broken_final_paths": 0,
        }

    for document_path in sorted(final_root.rglob("document.pdf")):
        folder = document_path.parent
        checked_dirs += 1
        missing = [
            name
            for name in ("document.pdf", "manifest.json", "references.json")
            if not (folder / name).exists()
        ]
        if missing:
            message = f"Composants manquants dans {folder}: {', '.join(missing)}"
            issues.append(message)
            alerts.append({"level": "CRITICAL", "message": message})
        else:
            complete_dirs += 1

        manifest_path = folder / "manifest.json"
        manifest = read_json(manifest_path, alerts)
        if isinstance(manifest, dict):
            check_path_consistency(final_root, folder, manifest, alerts)

    for row in selected_records:
        if not str(row.get("sha256", "")).strip():
            alerts.append(
                {
                    "level": "WARNING",
                    "message": (
                        "Document selectionne sans sha256: "
                        f"{row.get('selected_canonical_document_id') or row.get('canonical_document_id')}"
                    ),
                }
            )
        exists = path_exists_from_value(row.get("final_path"), run_dir)
        if exists is False:
            broken_final_paths += 1
            alerts.append(
                {
                    "level": "CRITICAL",
                    "message": f"final_path casse: {row.get('final_path')}",
                }
            )

    return {
        "checked_dirs": checked_dirs,
        "complete_dirs": complete_dirs,
        "missing_components": issues,
        "broken_final_paths": broken_final_paths,
    }


def check_path_consistency(
    final_root: Path, folder: Path, manifest: dict[str, Any], alerts: list[dict[str, str]]
) -> None:
    try:
        relative_parts = folder.relative_to(final_root).parts
    except ValueError:
        return
    if len(relative_parts) < 3:
        alerts.append(
            {
                "level": "WARNING",
                "message": f"Chemin ESGFinalCorpus inattendu: {folder}",
            }
        )
        return

    company_slug, year, official_doc_type = relative_parts[:3]
    manifest_company = str(manifest.get("company_slug", "")).strip()
    manifest_year = str(
        manifest.get("fiscal_year") or manifest.get("reference_year") or ""
    ).strip()
    manifest_doc_type = str(manifest.get("official_doc_type", "")).strip()

    if manifest_company and manifest_company != company_slug:
        alerts.append(
            {
                "level": "WARNING",
                "message": (
                    f"company_slug incoherent: chemin={company_slug}, "
                    f"manifest={manifest_company}, dossier={folder}"
                ),
            }
        )
    if manifest_year and manifest_year != year:
        alerts.append(
            {
                "level": "WARNING",
                "message": (
                    f"annee incoherente: chemin={year}, manifest={manifest_year}, "
                    f"dossier={folder}"
                ),
            }
        )
    if manifest_doc_type and manifest_doc_type != official_doc_type:
        alerts.append(
            {
                "level": "WARNING",
                "message": (
                    f"official_doc_type incoherent: chemin={official_doc_type}, "
                    f"manifest={manifest_doc_type}, dossier={folder}"
                ),
            }
        )
    if not str(manifest.get("sha256", "")).strip():
        alerts.append(
            {
                "level": "WARNING",
                "message": f"Document sans sha256 dans manifest: {folder / 'manifest.json'}",
            }
        )


def audit_manifest_pdf_references(run_dir: Path, alerts: list[dict[str, str]]) -> dict[str, int]:
    checked = 0
    missing = 0
    unreadable = 0
    path_keys = {
        "organized_local_path",
        "taxonomy_document_path",
        "final_path",
        "source_path",
        "canonical_local_path",
    }

    for manifest_path in run_dir.rglob("manifest.json"):
        manifest = read_json(manifest_path, alerts)
        if not isinstance(manifest, dict):
            unreadable += 1
            continue
        for key in path_keys:
            value = manifest.get(key)
            if not value or not str(value).lower().endswith(".pdf"):
                continue
            checked += 1
            exists = path_exists_from_value(value, run_dir)
            if exists is False:
                missing += 1
                alerts.append(
                    {
                        "level": "WARNING",
                        "message": f"PDF reference absent dans {manifest_path}: {key}={value}",
                    }
                )

    return {
        "manifest_pdf_references_checked": checked,
        "manifest_pdf_references_missing": missing,
        "manifest_unreadable": unreadable,
    }


def add_business_alerts(
    task_state: dict[str, Any],
    post_state: dict[str, Any],
    physical_state: dict[str, Any],
    alerts: list[dict[str, str]],
) -> None:
    if task_state["failed"]:
        alerts.append(
            {
                "level": "CRITICAL",
                "message": f"{task_state['failed']} tache(s) en echec dans task_log/final_summary.",
            }
        )
    if not physical_state["exists"].get("ESGFinalCorpus"):
        alerts.append({"level": "CRITICAL", "message": "ESGFinalCorpus absent."})
    if physical_state["pdf_counts"].get("ESGFinalCorpus", 0) == 0:
        alerts.append({"level": "CRITICAL", "message": "Aucun PDF dans ESGFinalCorpus."})

    for key, label in (
        ("selected_needs_review", "documents selectionnes a revoir"),
        ("likely_wrong_company", "documents probablement mauvaise entreprise"),
        ("needs_review", "documents a revoir"),
    ):
        count = int(post_state.get(key, 0) or 0)
        if count:
            alerts.append({"level": "WARNING", "message": f"{count} {label}."})

    run_config = task_state.get("run_config") or {}
    expected_companies = run_config.get("companies")
    if isinstance(expected_companies, list) and post_state["records"].get("selected"):
        selected_companies = {
            str(row.get("company_slug", "")).strip()
            for row in post_state["records"]["selected"]
            if str(row.get("company_slug", "")).strip()
        }
        for company in expected_companies:
            company_text = str(company).strip().lower().replace(" ", "-")
            if company_text and company_text not in selected_companies:
                alerts.append(
                    {
                        "level": "WARNING",
                        "message": f"Entreprise attendue sans document final selectionne: {company}",
                    }
                )


def build_markdown(
    run_dir: Path,
    audit_date: str,
    task_state: dict[str, Any],
    post_state: dict[str, Any],
    physical_state: dict[str, Any],
    final_audit: dict[str, Any],
    manifest_ref_audit: dict[str, int],
    alerts: list[dict[str, str]],
) -> str:
    alert_counts = Counter(alert["level"] for alert in alerts)
    conclusion = build_conclusion(alert_counts, task_state, physical_state)

    lines = [
        "# Rapport d'audit du run ESG",
        "",
        "## 1. Resume du run",
        "",
        f"- Chemin du run: `{run_dir}`",
        f"- Date d'audit: `{audit_date}`",
        f"- Dossier postprocessing present: {bool_text(physical_state['exists']['postprocessing'])}",
        f"- Dossier ESGCorpus present: {bool_text(physical_state['exists']['ESGCorpus'])}",
        f"- Dossier ESGCorpusTaxonomy present: {bool_text(physical_state['exists']['ESGCorpusTaxonomy'])}",
        f"- Dossier ESGFinalCorpus present: {bool_text(physical_state['exists']['ESGFinalCorpus'])}",
        "",
        "## 2. Etat des taches orchestrateur",
        "",
        "| Fichier | Present |",
        "|---|---:|",
        f"| task_log.csv | {bool_text(task_state['exists']['task_log'])} |",
        f"| run_state.json | {bool_text(task_state['exists']['run_state'])} |",
        f"| final_summary.json | {bool_text(task_state['exists']['final_summary'])} |",
        f"| coverage_matrix.csv | {bool_text(task_state['exists']['coverage_matrix'])} |",
        "",
        f"- Nombre total de taches: {task_state['total_tasks']}",
        f"- success: {task_state['success']}",
        f"- failed: {task_state['failed']}",
        f"- skipped_not_applicable: {task_state['skipped_not_applicable']}",
        f"- autres statuts: {task_state['other_statuses'] or {}}",
        "",
        "### Repartition par entreprise",
        "",
        table_from_counts(task_state["by_company"]),
        "",
        "### Repartition par annee",
        "",
        table_from_counts(task_state["by_year"]),
        "",
        "### Repartition par type documentaire",
        "",
        table_from_counts(task_state["by_doc_type"]),
        "",
        "## 3. Etat du post-processing",
        "",
        "| Sortie | Presente | Chemin |",
        "|---|---:|---|",
    ]

    for key, path in post_state["paths"].items():
        lines.append(
            f"| {key} | {bool_text(post_state['exists'][key])} | `{escape_md(path)}` |"
        )

    lines.extend(
        [
            "",
            f"- Documents dans le registre central: {post_state['central_documents']}",
            f"- Documents uniques: {post_state['unique_documents']}",
            f"- Groupes de doublons: {post_state['duplicate_groups']}",
            f"- Documents valides/audites par validation: {post_state['validated_documents']}",
            f"- Documents selectionnes: {post_state['selected_documents']}",
            f"- Documents rejetes: {post_state['rejected_documents']}",
            f"- Documents needs_review: {post_state['needs_review']}",
            f"- Documents likely_wrong_company: {post_state['likely_wrong_company']}",
            f"- Documents selected_needs_review: {post_state['selected_needs_review']}",
            "",
            "### Statuts de selection",
            "",
            table_from_counts(post_state["selection_status_counts"]),
            "",
            "### Statuts de rejet",
            "",
            table_from_counts(post_state["rejection_status_counts"]),
            "",
            "## 4. Etat des dossiers physiques",
            "",
            "| Dossier | Present | PDF |",
            "|---|---:|---:|",
        ]
    )
    for key in ("postprocessing", "ESGCorpus", "ESGCorpusTaxonomy", "ESGFinalCorpus"):
        lines.append(
            f"| {key} | {bool_text(physical_state['exists'][key])} | {physical_state['pdf_counts'][key]} |"
        )
    lines.extend(
        [
            "",
            f"- manifest.json trouves: {physical_state['manifest_json']}",
            f"- references.json trouves: {physical_state['references_json']}",
            "",
            "## 5. Coherence attendue / observee",
            "",
            f"- Dossiers ESGFinalCorpus verifies: {final_audit['checked_dirs']}",
            f"- Dossiers complets avec document.pdf, manifest.json, references.json: {final_audit['complete_dirs']}",
            f"- final_path casses: {final_audit['broken_final_paths']}",
            f"- References PDF dans manifests verifiees: {manifest_ref_audit['manifest_pdf_references_checked']}",
            f"- References PDF absentes: {manifest_ref_audit['manifest_pdf_references_missing']}",
            f"- Manifests illisibles: {manifest_ref_audit['manifest_unreadable']}",
            "",
            "## 6. Alertes",
            "",
        ]
    )
    for level in ("CRITICAL", "WARNING", "INFO"):
        level_alerts = [alert for alert in alerts if alert["level"] == level]
        lines.append(f"### {level}")
        lines.append("")
        if level_alerts:
            for alert in level_alerts:
                lines.append(f"- {escape_md(alert['message'])}")
        else:
            lines.append("- Aucune alerte.")
        lines.append("")

    lines.extend(
        [
            "## 7. Conclusion",
            "",
            conclusion,
            "",
        ]
    )
    return "\n".join(lines)


def build_conclusion(
    alert_counts: Counter[str], task_state: dict[str, Any], physical_state: dict[str, Any]
) -> str:
    if alert_counts.get("CRITICAL", 0):
        return (
            "Run non exploitable tel quel pour une extraction ESG. "
            "Des alertes CRITICAL doivent etre corrigees ou acceptees explicitement "
            "avant toute etape d'extraction."
        )
    if task_state.get("failed", 0):
        return (
            "Run a revoir avant extraction ESG: des taches ont echoue meme si les "
            "sorties physiques peuvent exister."
        )
    if physical_state["pdf_counts"].get("ESGFinalCorpus", 0) == 0:
        return (
            "Run non pret pour extraction ESG: aucun document final n'a ete detecte."
        )
    if alert_counts.get("WARNING", 0):
        return (
            "Run potentiellement exploitable pour audit humain, mais extraction ESG "
            "a differer tant que les WARNING importants ne sont pas qualifies."
        )
    return (
        "Run exploitable du point de vue documentaire. Une extraction ESG peut etre "
        "envisagee apres validation metier du perimetre."
    )


def write_outputs(
    run_dir: Path,
    markdown: str,
    summary: dict[str, Any],
) -> None:
    report_path = run_dir / "audit_report.md"
    summary_path = run_dir / "audit_summary.json"
    report_path.write_text(markdown, encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit non destructif des sorties d'un run ESGOrchestrator."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Chemin vers ESGOrchestrator/runs/<run_id>.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    alerts: list[dict[str, str]] = []
    audit_date = utc_now()

    if not run_dir.exists() or not run_dir.is_dir():
        raise SystemExit(f"Run dir introuvable ou invalide: {run_dir}")

    task_state = collect_task_state(run_dir, alerts)
    post_state = collect_postprocessing_state(run_dir, alerts)
    physical_state = collect_physical_state(run_dir)
    final_audit = audit_final_corpus(
        run_dir, post_state["records"].get("selected", []), alerts
    )
    manifest_ref_audit = audit_manifest_pdf_references(run_dir, alerts)
    add_business_alerts(task_state, post_state, physical_state, alerts)

    alert_counts = dict(Counter(alert["level"] for alert in alerts))
    summary = {
        "run_dir": as_posix(run_dir),
        "audit_date": audit_date,
        "task_state": task_state,
        "postprocessing_state": {
            key: value
            for key, value in post_state.items()
            if key != "records"
        },
        "physical_state": physical_state,
        "final_corpus_audit": final_audit,
        "manifest_reference_audit": manifest_ref_audit,
        "alert_counts": alert_counts,
        "alerts": alerts,
    }

    markdown = build_markdown(
        run_dir,
        audit_date,
        task_state,
        post_state,
        physical_state,
        final_audit,
        manifest_ref_audit,
        alerts,
    )
    write_outputs(run_dir, markdown, summary)

    print(f"Audit report written: {run_dir / 'audit_report.md'}")
    print(f"Audit summary written: {run_dir / 'audit_summary.json'}")
    print(f"Alerts: {alert_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
