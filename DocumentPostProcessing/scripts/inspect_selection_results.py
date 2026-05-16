from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELECTION_DIR = PROJECT_ROOT / "data" / "selection"


def shorten(value, max_len: int = 100) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def print_table(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)
    if df.empty:
        print("(aucune ligne)")
        return
    if max_rows is not None:
        df = df.head(max_rows)
    print(df.to_string(index=False))


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    selected_path = SELECTION_DIR / "selected_documents.csv"
    rejected_path = SELECTION_DIR / "rejected_documents.csv"
    summary_path = SELECTION_DIR / "document_selection_summary.json"

    if not selected_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {selected_path}")
    if not rejected_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {rejected_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {summary_path}")

    selected = pd.read_csv(selected_path)
    rejected = pd.read_csv(rejected_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return selected, rejected, summary


def inspect_sidecars(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in selected.iterrows():
        final_path = Path(str(row.get("final_path")))
        parent = final_path.parent
        rows.append(
            {
                "company_slug": row.get("company_slug"),
                "fiscal_year": row.get("fiscal_year"),
                "official_doc_type": row.get("official_doc_type"),
                "final_path_exists": final_path.exists(),
                "document_pdf_exists": (parent / "document.pdf").exists(),
                "manifest_json_exists": (parent / "manifest.json").exists(),
                "references_json_exists": (parent / "references.json").exists(),
                "final_path": str(final_path),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    selected, rejected, summary = load_inputs()

    selected_status_counts = selected["selection_status"].value_counts().to_dict()
    rejection_status_counts = rejected["rejection_status"].value_counts().to_dict()

    print("\n=== Synthese globale selection finale ===")
    print(f"status: {summary.get('status')}")
    print(f"documents selectionnes: {len(selected)}")
    print(f"documents rejetes: {len(rejected)}")
    print(f"selected: {selected_status_counts.get('selected', 0)}")
    print(f"selected_needs_review: {selected_status_counts.get('selected_needs_review', 0)}")
    print(f"likely_wrong_company: {rejection_status_counts.get('likely_wrong_company', 0)}")
    print(f"needs_review: {rejection_status_counts.get('needs_review', 0)}")
    print(f"rejected: {rejection_status_counts.get('rejected', 0)}")

    print_table(
        "Repartition selectionnee par company_slug",
        selected["company_slug"].value_counts().rename_axis("company_slug").reset_index(name="count"),
    )

    print_table(
        "Repartition selectionnee par fiscal_year",
        selected["fiscal_year"].value_counts().sort_index().rename_axis("fiscal_year").reset_index(name="count"),
    )

    print_table(
        "Repartition selectionnee par official_doc_type",
        selected["official_doc_type"].value_counts().sort_index().rename_axis("official_doc_type").reset_index(name="count"),
    )

    print_table(
        "Repartition selectionnee par selection_status",
        selected["selection_status"].value_counts().sort_index().rename_axis("selection_status").reset_index(name="count"),
    )

    selected_needs_review = selected[
        selected["selection_status"] == "selected_needs_review"
    ].copy()
    if not selected_needs_review.empty:
        selected_needs_review["source_title"] = selected_needs_review["source_title"].apply(shorten)
        selected_needs_review["final_path"] = selected_needs_review["final_path"].apply(
            lambda value: shorten(value, 140)
        )
    print_table(
        "Documents selectionnes en selected_needs_review",
        selected_needs_review[
            [
                "company_name",
                "fiscal_year",
                "official_doc_type",
                "source_title",
                "selection_reason",
                "final_path",
            ]
        ] if not selected_needs_review.empty else selected_needs_review,
    )

    likely_wrong = rejected[rejected["rejection_status"] == "likely_wrong_company"].copy()
    if not likely_wrong.empty:
        likely_wrong["source_title"] = likely_wrong["source_title"].apply(shorten)
        likely_wrong["source_path"] = likely_wrong["source_path"].apply(
            lambda value: shorten(value, 140)
        )
    print_table(
        "Documents rejetes likely_wrong_company",
        likely_wrong[
            [
                "company_name",
                "fiscal_year",
                "official_doc_type",
                "source_title",
                "rejection_reason",
                "source_path",
            ]
        ] if not likely_wrong.empty else likely_wrong,
    )

    top_rejection_reasons = (
        rejected["rejection_reason"]
        .value_counts()
        .head(15)
        .rename_axis("rejection_reason")
        .reset_index(name="count")
    )
    print_table("Top raisons de rejet", top_rejection_reasons)

    sidecar_check = inspect_sidecars(selected)
    anomalies = sidecar_check[
        ~(
            sidecar_check["final_path_exists"]
            & sidecar_check["document_pdf_exists"]
            & sidecar_check["manifest_json_exists"]
            & sidecar_check["references_json_exists"]
        )
    ]

    print("\n=== Verification fichiers finaux ===")
    print(f"documents selectionnes controles: {len(sidecar_check)}")
    print(f"anomalies detectees: {len(anomalies)}")

    if not anomalies.empty:
        print_table(
            "Anomalies fichiers finaux",
            anomalies[
                [
                    "company_slug",
                    "fiscal_year",
                    "official_doc_type",
                    "final_path_exists",
                    "document_pdf_exists",
                    "manifest_json_exists",
                    "references_json_exists",
                    "final_path",
                ]
            ],
        )


if __name__ == "__main__":
    main()
