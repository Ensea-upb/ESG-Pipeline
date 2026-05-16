from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd

from .scope import filter_dataframe_scope


COMPLETE_DOC_TYPES = {
    "01_urd_annual_report",
    "02_sustainability_statement_csrd_esrs",
    "03_climate_report_tcfd_transition_plan",
    "04_vigilance_plan",
    "05_half_year_financial_report",
}


@dataclass
class DocumentSelectionResult:
    status: str
    message: str
    total_batches: int
    total_input_documents: int
    total_selected_documents: int
    total_rejected_documents: int
    total_selected_needs_review: int
    total_redundant_same_hash: int
    total_integrated_in_urd: int
    total_superseded_by_csrd_statement: int
    total_likely_wrong_company: int
    total_errors: int
    output_final_corpus_root: str
    selected_csv_path: str
    selected_json_path: str
    rejected_csv_path: str
    summary_path: str
    errors: list[dict] = field(default_factory=list)


class DocumentSelector:
    """
    Selection finale offline des documents par couple entreprise / annee.

    Le selecteur ne modifie pas les corpus sources. Il copie uniquement les
    documents selectionnes vers ESGFinalCorpus.
    """

    def __init__(
        self,
        taxonomy_index_csv_path: str | Path = (
            "data/organized_corpus_taxonomy/taxonomy_organized_documents_index.csv"
        ),
        validation_results_csv_path: str | Path = (
            "data/validation/document_validation_results.csv"
        ),
        output_final_corpus_root: str | Path = "../ESGFinalCorpus",
        output_dir: str | Path = "data/selection",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.taxonomy_index_csv_path = Path(taxonomy_index_csv_path)
        self.validation_results_csv_path = Path(validation_results_csv_path)
        self.output_final_corpus_root = Path(output_final_corpus_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def select(self) -> DocumentSelectionResult:
        taxonomy_df = self.load_taxonomy_index()
        validation_df = self.load_validation_results()
        merged = self.merge_inputs(taxonomy_df, validation_df)

        self.output_final_corpus_root.mkdir(parents=True, exist_ok=True)

        selected_rows: list[dict] = []
        rejected_rows: list[dict] = []
        errors: list[dict] = []

        batch_keys = ["company_slug", "fiscal_year"]
        grouped = merged.groupby(batch_keys, dropna=False, sort=True)

        for (company_slug, fiscal_year), batch in grouped:
            try:
                selected, rejected = self.process_batch(batch)
                selected_rows.extend(selected)
                rejected_rows.extend(rejected)
            except Exception as exc:
                error = {
                    "company_slug": self.safe_value(company_slug),
                    "fiscal_year": self.safe_int_or_none(fiscal_year),
                    "error": str(exc),
                }
                errors.append(error)
                for _, row in batch.iterrows():
                    rejected_rows.append(
                        self.build_rejected_row(
                            row=row,
                            rejection_status="rejected",
                            rejection_reason=f"batch_error: {exc}",
                        )
                    )

        output_selected_csv = self.output_dir / "selected_documents.csv"
        output_selected_json = self.output_dir / "selected_documents.json"
        output_rejected_csv = self.output_dir / "rejected_documents.csv"
        summary_path = self.output_dir / "document_selection_summary.json"

        self.save_outputs(
            selected_rows=selected_rows,
            rejected_rows=rejected_rows,
            selected_csv_path=output_selected_csv,
            selected_json_path=output_selected_json,
            rejected_csv_path=output_rejected_csv,
        )

        summary = self.build_summary(
            input_count=len(merged),
            batch_count=len(grouped),
            selected_rows=selected_rows,
            rejected_rows=rejected_rows,
            errors=errors,
            selected_csv_path=output_selected_csv,
            selected_json_path=output_selected_json,
            rejected_csv_path=output_rejected_csv,
            summary_path=summary_path,
        )
        summary_path.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    def process_batch(self, batch: pd.DataFrame) -> tuple[list[dict], list[dict]]:
        selected_rows: list[dict] = []
        rejected_rows: list[dict] = []

        batch = batch.copy()
        has_urd = self.batch_has_selectable_doc_type(batch, "01_urd_annual_report")
        has_csrd = self.batch_has_selectable_doc_type(
            batch,
            "02_sustainability_statement_csrd_esrs",
        )

        seen_doc_type_keys: set[tuple[str, str]] = set()

        for official_doc_type, group in batch.groupby("official_doc_type", dropna=False):
            if not self.has_value(official_doc_type):
                for _, row in group.iterrows():
                    rejected_rows.append(
                        self.build_rejected_row(
                            row=row,
                            rejection_status="needs_review",
                            rejection_reason="official_doc_type_missing_or_needs_review",
                        )
                    )
                continue

            group = self.drop_unreadable(group, rejected_rows)
            if group.empty:
                continue

            group = self.reject_same_hash_duplicates(group, rejected_rows)
            if group.empty:
                continue

            group = self.reject_wrong_company_when_alternatives_exist(
                group,
                rejected_rows,
            )
            if group.empty:
                continue

            if (
                str(official_doc_type) == "01_urd_annual_report"
                and has_urd
            ):
                group = self.reject_integrated_technical_sections(group, rejected_rows)
                if group.empty:
                    continue

            if (
                str(official_doc_type) == "02_sustainability_statement_csrd_esrs"
                and has_csrd
            ):
                group = self.reject_superseded_sustainability_docs(group, rejected_rows)
                if group.empty:
                    continue

            ranked = group.copy()
            ranked["_selection_score"] = ranked.apply(self.selection_score, axis=1)
            ranked = ranked.sort_values(
                by=[
                    "_selection_score",
                    "validation_score",
                    "source_official_score",
                    "page_count_sort",
                    "duplicate_count_sort",
                    "canonical_document_id",
                ],
                ascending=[False, False, False, False, False, True],
                kind="mergesort",
            )

            selected_row = ranked.iloc[0]
            selected_status = self.selection_status_for_row(selected_row)
            selected_reason = self.selection_reason_for_row(selected_row)

            selected_rows.append(
                self.copy_selected_document(
                    row=selected_row,
                    selection_status=selected_status,
                    selection_reason=selected_reason,
                )
            )

            selected_key = (
                str(selected_row.get("official_doc_type")),
                str(selected_row.get("canonical_document_id")),
            )
            seen_doc_type_keys.add(selected_key)

            for _, row in ranked.iloc[1:].iterrows():
                duplicate_key = (
                    str(row.get("official_doc_type")),
                    str(row.get("canonical_document_id")),
                )
                status = "redundant_same_doc_type"
                reason = "higher_ranked_document_selected_for_same_official_doc_type"
                if row.get("document_validation_status") == "likely_wrong_company":
                    status = "likely_wrong_company"
                    reason = "alternative_exists_for_same_official_doc_type"
                if duplicate_key in seen_doc_type_keys:
                    status = "redundant_same_hash"
                    reason = "same_canonical_document_already_selected_for_doc_type"
                rejected_rows.append(
                    self.build_rejected_row(
                        row=row,
                        rejection_status=status,
                        rejection_reason=reason,
                    )
                )

        return selected_rows, rejected_rows

    def drop_unreadable(
        self,
        group: pd.DataFrame,
        rejected_rows: list[dict],
    ) -> pd.DataFrame:
        keep_rows = []
        for _, row in group.iterrows():
            technical_status = str(row.get("technical_validation_status") or "")
            document_status = str(row.get("document_validation_status") or "")
            if technical_status in {"missing_file", "not_pdf", "unreadable_pdf"}:
                rejected_rows.append(
                    self.build_rejected_row(
                        row=row,
                        rejection_status="unreadable",
                        rejection_reason=f"technical_validation_status={technical_status}",
                    )
                )
                continue
            if document_status == "unreadable":
                rejected_rows.append(
                    self.build_rejected_row(
                        row=row,
                        rejection_status="unreadable",
                        rejection_reason="document_validation_status=unreadable",
                    )
                )
                continue
            keep_rows.append(row)

        if not keep_rows:
            return pd.DataFrame(columns=group.columns)
        return pd.DataFrame(keep_rows)

    def reject_same_hash_duplicates(
        self,
        group: pd.DataFrame,
        rejected_rows: list[dict],
    ) -> pd.DataFrame:
        kept = []
        for _, hash_group in group.groupby("sha256", dropna=False):
            if len(hash_group) == 1:
                kept.append(hash_group.iloc[0])
                continue

            ranked = hash_group.copy()
            ranked["_selection_score"] = ranked.apply(self.selection_score, axis=1)
            ranked = ranked.sort_values(
                by=["_selection_score", "canonical_document_id"],
                ascending=[False, True],
                kind="mergesort",
            )
            kept.append(ranked.iloc[0])
            for _, row in ranked.iloc[1:].iterrows():
                rejected_rows.append(
                    self.build_rejected_row(
                        row=row,
                        rejection_status="redundant_same_hash",
                        rejection_reason="same_sha256_within_same_official_doc_type",
                    )
                )

        if not kept:
            return pd.DataFrame(columns=group.columns)
        return pd.DataFrame(kept)

    def reject_wrong_company_when_alternatives_exist(
        self,
        group: pd.DataFrame,
        rejected_rows: list[dict],
    ) -> pd.DataFrame:
        wrong_mask = group["document_validation_status"] == "likely_wrong_company"
        if not wrong_mask.any() or wrong_mask.all():
            return group

        for _, row in group[wrong_mask].iterrows():
            rejected_rows.append(
                self.build_rejected_row(
                    row=row,
                    rejection_status="likely_wrong_company",
                    rejection_reason="alternative_exists_for_same_official_doc_type",
                )
            )

        return group[~wrong_mask].copy()

    def reject_integrated_technical_sections(
        self,
        group: pd.DataFrame,
        rejected_rows: list[dict],
    ) -> pd.DataFrame:
        kept = []
        for _, row in group.iterrows():
            technical_family = str(row.get("technical_document_family") or "")
            if technical_family in {"governance_report", "remuneration_report"}:
                rejected_rows.append(
                    self.build_rejected_row(
                        row=row,
                        rejection_status="integrated_in_urd",
                        rejection_reason="governance_or_remuneration_section_integrated_in_urd",
                    )
                )
                continue
            kept.append(row)
        if not kept:
            return pd.DataFrame(columns=group.columns)
        return pd.DataFrame(kept)

    def reject_superseded_sustainability_docs(
        self,
        group: pd.DataFrame,
        rejected_rows: list[dict],
    ) -> pd.DataFrame:
        csrd_mask = group.apply(self.looks_like_csrd_statement, axis=1)
        if not csrd_mask.any():
            return group

        csrd_candidates = group[csrd_mask].copy()
        non_csrd = group[~csrd_mask].copy()
        for _, row in non_csrd.iterrows():
            rejected_rows.append(
                self.build_rejected_row(
                    row=row,
                    rejection_status="superseded_by_csrd_statement",
                    rejection_reason="csrd_or_esrs_statement_available_for_same_batch",
                )
            )
        return csrd_candidates

    def copy_selected_document(
        self,
        row: pd.Series,
        selection_status: str,
        selection_reason: str,
    ) -> dict:
        source_pdf = Path(str(row.get("taxonomy_document_path")))
        source_manifest = Path(str(row.get("taxonomy_manifest_path")))
        source_references = Path(str(row.get("taxonomy_references_path")))
        target_dir = self.build_target_dir(row)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_pdf = target_dir / "document.pdf"
        target_manifest = target_dir / "manifest.json"
        target_references = target_dir / "references.json"

        self.copy_file_checked(source_pdf, target_pdf, str(row.get("sha256")))
        self.copy_sidecar(source_manifest, target_manifest)
        self.copy_sidecar(source_references, target_references)

        return self.build_selected_row(
            row=row,
            final_path=str(target_pdf.resolve()),
            selection_status=selection_status,
            selection_reason=selection_reason,
        )

    def build_target_dir(self, row: pd.Series) -> Path:
        return (
            self.output_final_corpus_root
            / self.slugify(row.get("company_slug") or row.get("company_name"))
            / str(self.safe_int_or_none(row.get("fiscal_year")) or "unknown_year")
            / str(row.get("official_doc_type"))
        )

    def selection_score(self, row: pd.Series) -> float:
        score = 0.0

        if row.get("technical_validation_status") == "valid_pdf":
            score += 1000
        if row.get("document_validation_status") == "likely_valid":
            score += 500
        elif row.get("document_validation_status") == "needs_review":
            score += 150
        elif row.get("document_validation_status") == "likely_wrong_company":
            score -= 700

        score += self.safe_float(row.get("validation_score")) or 0
        score += self.source_official_score(row) * 40

        if self.safe_bool(row.get("company_name_detected_in_text")):
            score += 30
        if self.target_year_detected(row):
            score += 25

        if str(row.get("official_doc_type")) in COMPLETE_DOC_TYPES:
            score += min(self.safe_float(row.get("page_count")) or 0, 500) * 0.2

        score += min(self.safe_float(row.get("duplicate_count")) or 0, 20) * 0.5
        return score

    def selection_status_for_row(self, row: pd.Series) -> str:
        if row.get("document_validation_status") == "likely_valid":
            return "selected"
        if row.get("document_validation_status") == "likely_wrong_company":
            return "selected_needs_review"
        return "selected_needs_review"

    def selection_reason_for_row(self, row: pd.Series) -> str:
        document_status = row.get("document_validation_status")
        if document_status == "likely_valid":
            return "best_ranked_likely_valid_document_for_official_doc_type"
        if document_status == "likely_wrong_company":
            return "selected_only_available_candidate_but_likely_wrong_company"
        return "selected_best_available_candidate_needs_review"

    @staticmethod
    def batch_has_selectable_doc_type(batch: pd.DataFrame, official_doc_type: str) -> bool:
        subset = batch[
            (batch["official_doc_type"] == official_doc_type)
            & (batch["technical_validation_status"] == "valid_pdf")
            & (batch["document_validation_status"] != "unreadable")
        ]
        return not subset.empty

    def build_selected_row(
        self,
        row: pd.Series,
        final_path: str,
        selection_status: str,
        selection_reason: str,
    ) -> dict:
        return {
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "official_doc_type": self.safe_value(row.get("official_doc_type")),
            "official_doc_type_label": self.safe_value(
                row.get("official_doc_type_label")
            ),
            "selected_canonical_document_id": self.safe_value(
                row.get("canonical_document_id")
            ),
            "sha256": self.safe_value(row.get("sha256")),
            "source_title": self.safe_value(row.get("source_title")),
            "source_url": self.safe_value(row.get("source_url")),
            "source_path": self.safe_value(row.get("taxonomy_document_path")),
            "final_path": final_path,
            "validation_status": self.safe_value(row.get("document_validation_status")),
            "selection_status": selection_status,
            "selection_reason": selection_reason,
            "selection_score": self.safe_float(row.get("_selection_score")),
            "page_count": self.safe_int_or_none(row.get("page_count")),
            "detected_years": self.safe_value(row.get("detected_years")),
            "company_name_detected_in_text": self.safe_bool(
                row.get("company_name_detected_in_text")
            ),
        }

    def build_rejected_row(
        self,
        row: pd.Series,
        rejection_status: str,
        rejection_reason: str,
    ) -> dict:
        return {
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "official_doc_type": self.safe_value(row.get("official_doc_type")),
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "source_title": self.safe_value(row.get("source_title")),
            "source_path": self.safe_value(row.get("taxonomy_document_path"))
            or self.safe_value(row.get("source_document_path")),
            "rejection_status": rejection_status,
            "rejection_reason": rejection_reason,
        }

    def load_taxonomy_index(self) -> pd.DataFrame:
        if not self.taxonomy_index_csv_path.exists():
            raise FileNotFoundError(
                f"Index taxonomique introuvable : {self.taxonomy_index_csv_path}"
            )
        df = pd.read_csv(self.taxonomy_index_csv_path)
        required = {
            "canonical_document_id",
            "sha256",
            "company_name",
            "company_slug",
            "fiscal_year",
            "technical_document_family",
            "official_doc_type",
            "official_doc_type_label",
            "status",
            "taxonomy_document_path",
            "taxonomy_manifest_path",
            "taxonomy_references_path",
        }
        self.validate_columns(df, required, "index taxonomique")
        return filter_dataframe_scope(df, self.company_slugs, self.years)

    def load_validation_results(self) -> pd.DataFrame:
        if not self.validation_results_csv_path.exists():
            raise FileNotFoundError(
                f"Resultats de validation introuvables : {self.validation_results_csv_path}"
            )
        df = pd.read_csv(self.validation_results_csv_path)
        required = {
            "canonical_document_id",
            "sha256",
            "document_family",
            "organized_local_path",
            "technical_validation_status",
            "document_validation_status",
            "page_count",
            "detected_years",
            "company_name_detected_in_text",
        }
        self.validate_columns(df, required, "resultats de validation")
        return filter_dataframe_scope(df, self.company_slugs, self.years)

    def merge_inputs(
        self,
        taxonomy_df: pd.DataFrame,
        validation_df: pd.DataFrame,
    ) -> pd.DataFrame:
        taxonomy_df = taxonomy_df.copy()
        validation_df = validation_df.copy()
        taxonomy_df["merge_key"] = taxonomy_df.apply(self.merge_key_for_taxonomy, axis=1)
        validation_df["merge_key"] = validation_df.apply(
            self.merge_key_for_validation,
            axis=1,
        )
        validation_subset = validation_df[
            [
                "merge_key",
                "technical_validation_status",
                "document_validation_status",
                "page_count",
                "detected_years",
                "company_name_detected_in_text",
                "detected_document_keywords",
                "validation_notes",
            ]
        ]
        merged = taxonomy_df.merge(validation_subset, on="merge_key", how="left")

        merged["technical_validation_status"] = merged[
            "technical_validation_status"
        ].fillna("needs_review")
        merged["document_validation_status"] = merged[
            "document_validation_status"
        ].fillna("needs_review")
        merged["page_count_sort"] = merged["page_count"].apply(
            lambda value: self.safe_float(value) or 0
        )
        merged["duplicate_count_sort"] = 1
        merged["validation_score"] = merged.apply(self.validation_score, axis=1)
        merged["source_official_score"] = merged.apply(
            self.source_official_score,
            axis=1,
        )
        merged["source_title"] = merged.apply(self.extract_source_title, axis=1)
        merged["source_url"] = merged.apply(self.extract_source_url, axis=1)
        return merged

    @staticmethod
    def merge_key_for_taxonomy(row: pd.Series) -> str:
        return "|".join(
            [
                str(row.get("canonical_document_id") or ""),
                str(row.get("technical_document_family") or ""),
            ]
        )

    @staticmethod
    def merge_key_for_validation(row: pd.Series) -> str:
        return "|".join(
            [
                str(row.get("canonical_document_id") or ""),
                str(row.get("document_family") or ""),
            ]
        )

    def validation_score(self, row: pd.Series) -> float:
        status = row.get("document_validation_status")
        if status == "likely_valid":
            return 100.0
        if status == "needs_review":
            return 50.0
        if status == "likely_wrong_company":
            return 5.0
        return 0.0

    def source_official_score(self, row: pd.Series) -> int:
        source_url = self.extract_source_url(row) or row.get("taxonomy_document_path")
        company_slug = self.safe_value(row.get("company_slug"))
        if not (source_url and company_slug):
            return 0
        netloc = urlparse(str(source_url)).netloc.lower()
        compact_netloc = netloc.replace("-", "").replace(".", "")
        compact_slug = str(company_slug).lower().replace("-", "")
        return int(bool(compact_slug and compact_slug in compact_netloc))

    def target_year_detected(self, row: pd.Series) -> bool:
        fiscal_year = self.safe_int_or_none(row.get("fiscal_year"))
        if fiscal_year is None:
            return False
        years = self.parse_json_list(row.get("detected_years"))
        parsed_years = {self.safe_int_or_none(year) for year in years}
        return fiscal_year in parsed_years

    def looks_like_csrd_statement(self, row: pd.Series) -> bool:
        text = self.normalize_text(
            " ".join(
                [
                    str(row.get("source_title") or ""),
                    str(row.get("detected_document_keywords") or ""),
                    str(row.get("taxonomy_notes") or ""),
                ]
            )
        )
        return any(marker in text for marker in ["csrd", "esrs", "sustainability statement"])

    def extract_source_title(self, row: pd.Series):
        manifest = self.load_json(row.get("taxonomy_manifest_path"))
        if manifest:
            return manifest.get("canonical_source_title")
        return None

    def extract_source_url(self, row: pd.Series):
        manifest = self.load_json(row.get("taxonomy_manifest_path"))
        if manifest:
            return manifest.get("canonical_source_url")
        return None

    @staticmethod
    def load_json(path_value: Any):
        if not DocumentSelector.has_value(path_value):
            return None
        path = Path(str(path_value))
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def copy_file_checked(self, source: Path, target: Path, expected_sha256: str) -> None:
        if not source.exists():
            raise FileNotFoundError(f"Fichier source introuvable : {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing_sha256 = self.compute_sha256(target)
            if existing_sha256 != expected_sha256:
                raise ValueError(
                    f"Fichier final existant avec SHA different : {target}"
                )
            return
        shutil.copy2(source, target)
        copied_sha256 = self.compute_sha256(target)
        if copied_sha256 != expected_sha256:
            target.unlink(missing_ok=True)
            raise ValueError(f"Copie invalide : {copied_sha256} != {expected_sha256}")

    @staticmethod
    def copy_sidecar(source: Path, target: Path) -> None:
        if source.exists():
            shutil.copy2(source, target)

    @staticmethod
    def compute_sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def save_outputs(
        selected_rows: list[dict],
        rejected_rows: list[dict],
        selected_csv_path: Path,
        selected_json_path: Path,
        rejected_csv_path: Path,
    ) -> None:
        pd.DataFrame(selected_rows).to_csv(
            selected_csv_path,
            index=False,
            encoding="utf-8-sig",
        )
        selected_json_path.write_text(
            json.dumps(selected_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        pd.DataFrame(rejected_rows).to_csv(
            rejected_csv_path,
            index=False,
            encoding="utf-8-sig",
        )

    def build_summary(
        self,
        input_count: int,
        batch_count: int,
        selected_rows: list[dict],
        rejected_rows: list[dict],
        errors: list[dict],
        selected_csv_path: Path,
        selected_json_path: Path,
        rejected_csv_path: Path,
        summary_path: Path,
    ) -> DocumentSelectionResult:
        selected_needs_review = sum(
            row.get("selection_status") == "selected_needs_review"
            for row in selected_rows
        )
        redundant_same_hash = sum(
            row.get("rejection_status") == "redundant_same_hash"
            for row in rejected_rows
        )
        integrated_in_urd = sum(
            row.get("rejection_status") == "integrated_in_urd"
            for row in rejected_rows
        )
        superseded_by_csrd = sum(
            row.get("rejection_status") == "superseded_by_csrd_statement"
            for row in rejected_rows
        )
        likely_wrong_company = sum(
            row.get("rejection_status") == "likely_wrong_company"
            for row in rejected_rows
        )

        status = "success" if not errors else "completed_with_errors"
        return DocumentSelectionResult(
            status=status,
            message=(
                f"Selection finale terminee : {len(selected_rows)} document(s) "
                f"selectionne(s), {len(rejected_rows)} document(s) rejetes."
            ),
            total_batches=batch_count,
            total_input_documents=input_count,
            total_selected_documents=len(selected_rows),
            total_rejected_documents=len(rejected_rows),
            total_selected_needs_review=selected_needs_review,
            total_redundant_same_hash=redundant_same_hash,
            total_integrated_in_urd=integrated_in_urd,
            total_superseded_by_csrd_statement=superseded_by_csrd,
            total_likely_wrong_company=likely_wrong_company,
            total_errors=len(errors),
            output_final_corpus_root=str(self.output_final_corpus_root),
            selected_csv_path=str(selected_csv_path),
            selected_json_path=str(selected_json_path),
            rejected_csv_path=str(rejected_csv_path),
            summary_path=str(summary_path),
            errors=errors,
        )

    @staticmethod
    def validate_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"Colonnes absentes de {label} : {', '.join(missing)}")

    @staticmethod
    def parse_json_list(value: Any) -> list:
        if not DocumentSelector.has_value(value):
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError:
            return [str(value)]
        if isinstance(parsed, list):
            return parsed
        return [parsed]

    @staticmethod
    def normalize_text(value: Any) -> str:
        text = str(value or "").lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def slugify(value: Any) -> str:
        text = str(value or "").lower().strip()
        text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        return text or "unknown"

    @staticmethod
    def has_value(value: Any) -> bool:
        if value is None:
            return False
        try:
            if pd.isna(value):
                return False
        except (TypeError, ValueError):
            pass
        return str(value).strip() != ""

    @staticmethod
    def safe_value(value: Any):
        if not DocumentSelector.has_value(value):
            return None
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @staticmethod
    def safe_float(value: Any) -> Optional[float]:
        if not DocumentSelector.has_value(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_int_or_none(value: Any) -> Optional[int]:
        if not DocumentSelector.has_value(value):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if not DocumentSelector.has_value(value):
            return False
        return str(value).strip().lower() in {"true", "1", "yes", "y"}
