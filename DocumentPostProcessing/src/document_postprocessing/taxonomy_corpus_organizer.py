from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .scope import filter_dataframe_scope


OFFICIAL_DOC_TYPES = {
    "01_urd_annual_report": {
        "label": "URD / annual report",
        "doc_type_stratum": "core_reporting",
        "period_type": "annual",
        "regulatory_status": "regulated_or_standard_reporting",
    },
    "02_sustainability_statement_csrd_esrs": {
        "label": "Sustainability statement / CSRD / ESRS",
        "doc_type_stratum": "core_sustainability",
        "period_type": "annual",
        "regulatory_status": "regulated_or_emerging_regulated",
    },
    "03_climate_report_tcfd_transition_plan": {
        "label": "Climate report / TCFD / transition plan",
        "doc_type_stratum": "climate",
        "period_type": "annual_or_ad_hoc",
        "regulatory_status": "voluntary_or_regulated",
    },
    "04_vigilance_plan": {
        "label": "Vigilance plan",
        "doc_type_stratum": "due_diligence",
        "period_type": "annual",
        "regulatory_status": "regulated",
    },
    "05_half_year_financial_report": {
        "label": "Half-year financial report",
        "doc_type_stratum": "financial_reporting",
        "period_type": "half_year",
        "regulatory_status": "regulated",
    },
    "06_us_sec_filing": {
        "label": "US SEC filing",
        "doc_type_stratum": "financial_reporting",
        "period_type": "annual_or_periodic",
        "regulatory_status": "regulated",
    },
    "07_code_ethique": {
        "label": "Code ethique / code of conduct",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "08_anticorruption_policy": {
        "label": "Anti-corruption policy",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "09_human_rights_policy": {
        "label": "Human rights policy",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "10_dei_policy": {
        "label": "DEI policy",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "11_environmental_policy": {
        "label": "Environmental policy",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "12_supplier_code_of_conduct": {
        "label": "Supplier code of conduct",
        "doc_type_stratum": "policy",
        "period_type": "perpetual",
        "regulatory_status": "policy",
    },
    "13_investor_presentations": {
        "label": "Investor presentations",
        "doc_type_stratum": "market_communication",
        "period_type": "ad_hoc",
        "regulatory_status": "voluntary",
    },
    "14_earnings_call_transcripts": {
        "label": "Earnings call transcripts",
        "doc_type_stratum": "market_communication",
        "period_type": "periodic",
        "regulatory_status": "voluntary",
    },
    "15_official_esg_press_releases": {
        "label": "Official ESG press releases",
        "doc_type_stratum": "market_communication",
        "period_type": "ad_hoc",
        "regulatory_status": "voluntary",
    },
    "16_agm_minutes_resolutions": {
        "label": "AGM minutes / resolutions",
        "doc_type_stratum": "governance",
        "period_type": "annual_or_ad_hoc",
        "regulatory_status": "regulated_or_official",
    },
    "17_cdp_response": {
        "label": "CDP response",
        "doc_type_stratum": "external_questionnaire",
        "period_type": "annual",
        "regulatory_status": "voluntary",
    },
    "18_sbti_validation": {
        "label": "SBTi validation",
        "doc_type_stratum": "external_validation",
        "period_type": "ad_hoc",
        "regulatory_status": "voluntary",
    },
    "19_third_party_assurance_report": {
        "label": "Third-party assurance report",
        "doc_type_stratum": "assurance",
        "period_type": "annual_or_ad_hoc",
        "regulatory_status": "regulated_or_voluntary",
    },
    "20_controversies_database": {
        "label": "Controversies database",
        "doc_type_stratum": "external_risk_signal",
        "period_type": "ad_hoc",
        "regulatory_status": "external_source",
    },
    "21_climate_human_rights_litigation": {
        "label": "Climate / human rights litigation",
        "doc_type_stratum": "external_risk_signal",
        "period_type": "ad_hoc",
        "regulatory_status": "external_source",
    },
    "22_critical_coverage": {
        "label": "Critical coverage",
        "doc_type_stratum": "external_risk_signal",
        "period_type": "ad_hoc",
        "regulatory_status": "external_source",
    },
}


DIRECT_FAMILY_MAPPING = {
    "annual_report": "01_urd_annual_report",
    "sustainability_report": "02_sustainability_statement_csrd_esrs",
    "climate_report": "03_climate_report_tcfd_transition_plan",
    "vigilance_plan": "04_vigilance_plan",
    "half_year_report": "05_half_year_financial_report",
    "investor_presentation": "13_investor_presentations",
    "earnings_call": "14_earnings_call_transcripts",
    "agm_document": "16_agm_minutes_resolutions",
    "cdp_response": "17_cdp_response",
    "sbti_commitment": "18_sbti_validation",
    "assurance_report": "19_third_party_assurance_report",
}


CORPORATE_POLICY_RULES = [
    (
        "12_supplier_code_of_conduct",
        ["supplier code", "code fournisseurs", "fournisseur", "responsible sourcing"],
        "supplier_code",
    ),
    (
        "08_anticorruption_policy",
        ["anti-corruption", "anticorruption", "anti bribery", "corruption"],
        "anticorruption_policy",
    ),
    (
        "09_human_rights_policy",
        ["human rights", "droits humains", "droit de l'homme"],
        "human_rights_policy",
    ),
    (
        "10_dei_policy",
        ["diversity", "inclusion", "dei", "diversite", "egalite"],
        "dei_policy",
    ),
    (
        "11_environmental_policy",
        ["environmental policy", "politique environnementale", "environnement"],
        "environmental_policy",
    ),
    (
        "07_code_ethique",
        ["code of conduct", "code ethique", "code of ethics", "ethics"],
        "code_ethique",
    ),
]


URD_MARKERS = [
    "annual report",
    "universal registration document",
    "document d'enregistrement universel",
    "rapport annuel",
    "urd",
    "deu",
]


@dataclass
class TaxonomyOrganizationResult:
    status: str
    message: str
    total_documents_processed: int
    total_copied_files: int
    total_existing_files: int
    total_missing_files: int
    total_needs_review: int
    total_errors: int
    distribution_by_official_doc_type: dict[str, int]
    output_corpus_root: str
    output_index_csv_path: str
    output_index_json_path: str
    summary_path: str
    errors: list[dict] = field(default_factory=list)


class TaxonomyCorpusOrganizer:
    """
    Reorganise ESGCorpus vers ESGCorpusTaxonomy selon les types officiels.

    Les fichiers source ne sont jamais deplaces. Les cas sans type officiel
    fiable sont indexes en needs_review et ne creent pas de dossier non officiel.
    """

    def __init__(
        self,
        organized_index_csv_path: str | Path = (
            "data/organized_corpus/organized_documents_index.csv"
        ),
        output_corpus_root: str | Path = "../ESGCorpusTaxonomy",
        output_dir: str | Path = "data/organized_corpus_taxonomy",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.organized_index_csv_path = Path(organized_index_csv_path)
        self.output_corpus_root = Path(output_corpus_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def organize(self) -> TaxonomyOrganizationResult:
        if not self.organized_index_csv_path.exists():
            raise FileNotFoundError(
                f"Index organise introuvable : {self.organized_index_csv_path}"
            )

        df = pd.read_csv(self.organized_index_csv_path)
        self.validate_columns(df)
        df = filter_dataframe_scope(df, self.company_slugs, self.years)
        self.output_corpus_root.mkdir(parents=True, exist_ok=True)

        index_rows: list[dict] = []
        errors: list[dict] = []
        total_copied = 0
        total_existing = 0
        total_missing = 0
        total_needs_review = 0

        for _, row in df.iterrows():
            source_path_value = self.safe_value(row.get("organized_document_path"))
            source_path = Path(str(source_path_value)) if source_path_value else None
            context = self.load_context(row)
            decision = self.classify_row(row, context)

            if decision["status"] == "needs_review":
                total_needs_review += 1
                index_rows.append(
                    self.build_index_row(
                        row=row,
                        decision=decision,
                        status="needs_review",
                    )
                )
                continue

            if not source_path or not source_path.exists():
                total_missing += 1
                index_rows.append(
                    self.build_index_row(
                        row=row,
                        decision=decision,
                        status="missing_file",
                        error_type="missing_file",
                        error_message=f"Fichier source introuvable : {source_path}",
                    )
                )
                continue

            expected_sha256 = str(row.get("sha256"))
            actual_sha256 = self.compute_sha256(source_path)
            if actual_sha256 != expected_sha256:
                error = {
                    "canonical_document_id": self.safe_value(
                        row.get("canonical_document_id")
                    ),
                    "sha256": expected_sha256,
                    "error_type": "source_sha256_mismatch",
                    "message": f"{actual_sha256} != {expected_sha256}",
                }
                errors.append(error)
                index_rows.append(
                    self.build_index_row(
                        row=row,
                        decision=decision,
                        status="error",
                        error_type=error["error_type"],
                        error_message=error["message"],
                    )
                )
                continue

            try:
                copy_status = self.copy_taxonomy_document(
                    row=row,
                    decision=decision,
                    source_path=source_path,
                    expected_sha256=expected_sha256,
                    context=context,
                )
                if copy_status == "copied":
                    total_copied += 1
                elif copy_status == "already_exists":
                    total_existing += 1
                index_rows.append(
                    self.build_index_row(row=row, decision=decision, status=copy_status)
                )
            except Exception as exc:
                error = {
                    "canonical_document_id": self.safe_value(
                        row.get("canonical_document_id")
                    ),
                    "sha256": expected_sha256,
                    "error_type": "copy_error",
                    "message": str(exc),
                }
                errors.append(error)
                index_rows.append(
                    self.build_index_row(
                        row=row,
                        decision=decision,
                        status="error",
                        error_type=error["error_type"],
                        error_message=error["message"],
                    )
                )

        output_index_json_path = self.output_dir / "taxonomy_organized_documents_index.json"
        output_index_csv_path = self.output_dir / "taxonomy_organized_documents_index.csv"
        summary_path = self.output_dir / "taxonomy_organization_summary.json"

        self.save_index(index_rows, output_index_json_path, output_index_csv_path)

        distribution = self.build_distribution(index_rows)
        status = "success" if not errors else "completed_with_errors"
        result = TaxonomyOrganizationResult(
            status=status,
            message=(
                f"Organisation taxonomy terminee : {total_copied} copie(s) creee(s), "
                f"{total_existing} deja presente(s), {total_needs_review} document(s) "
                f"a revoir."
            ),
            total_documents_processed=len(df),
            total_copied_files=total_copied,
            total_existing_files=total_existing,
            total_missing_files=total_missing,
            total_needs_review=total_needs_review,
            total_errors=len(errors),
            distribution_by_official_doc_type=distribution,
            output_corpus_root=str(self.output_corpus_root),
            output_index_csv_path=str(output_index_csv_path),
            output_index_json_path=str(output_index_json_path),
            summary_path=str(summary_path),
            errors=errors,
        )

        summary_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return result

    def classify_row(self, row: pd.Series, context: dict) -> dict:
        family = str(self.safe_value(row.get("document_family")) or "")
        searchable_text = self.normalize_text(
            " ".join(
                [
                    family,
                    str(self.safe_value(row.get("source_path")) or ""),
                    context.get("manifest_text", ""),
                    context.get("references_text", ""),
                ]
            )
        )

        if family in DIRECT_FAMILY_MAPPING:
            return self.build_decision(
                official_doc_type=DIRECT_FAMILY_MAPPING[family],
                doc_subtype=family,
            )

        if family == "corporate_policy":
            for official_doc_type, markers, doc_subtype in CORPORATE_POLICY_RULES:
                if any(self.normalize_text(marker) in searchable_text for marker in markers):
                    return self.build_decision(
                        official_doc_type=official_doc_type,
                        doc_subtype=doc_subtype,
                    )
            return {
                "status": "needs_review",
                "official_doc_type": None,
                "official_doc_type_label": None,
                "doc_type_stratum": None,
                "doc_subtype": "corporate_policy_needs_review",
                "period_type": "perpetual",
                "regulatory_status": "policy",
                "parent_doc_id": None,
                "notes": ["corporate_policy_needs_review"],
            }

        if family in {"governance_report", "remuneration_report"}:
            if any(self.normalize_text(marker) in searchable_text for marker in URD_MARKERS):
                return self.build_decision(
                    official_doc_type="01_urd_annual_report",
                    doc_subtype=f"{family}_section_or_extract",
                    notes=["may_be_section_of_urd"],
                )
            return {
                "status": "needs_review",
                "official_doc_type": None,
                "official_doc_type_label": None,
                "doc_type_stratum": None,
                "doc_subtype": f"{family}_needs_review",
                "period_type": None,
                "regulatory_status": None,
                "parent_doc_id": None,
                "notes": ["may_be_section_of_urd", "official_doc_type_needs_review"],
            }

        return {
            "status": "needs_review",
            "official_doc_type": None,
            "official_doc_type_label": None,
            "doc_type_stratum": None,
            "doc_subtype": f"{family or 'unknown'}_needs_review",
            "period_type": None,
            "regulatory_status": None,
            "parent_doc_id": None,
            "notes": ["official_doc_type_needs_review"],
        }

    @staticmethod
    def build_decision(
        official_doc_type: str,
        doc_subtype: Optional[str] = None,
        notes: Optional[list[str]] = None,
    ) -> dict:
        metadata = OFFICIAL_DOC_TYPES[official_doc_type]
        return {
            "status": "mapped",
            "official_doc_type": official_doc_type,
            "official_doc_type_label": metadata["label"],
            "doc_type_stratum": metadata["doc_type_stratum"],
            "doc_subtype": doc_subtype,
            "period_type": metadata["period_type"],
            "regulatory_status": metadata["regulatory_status"],
            "parent_doc_id": None,
            "notes": notes or [],
        }

    def copy_taxonomy_document(
        self,
        row: pd.Series,
        decision: dict,
        source_path: Path,
        expected_sha256: str,
        context: dict,
    ) -> str:
        target_dir = self.build_target_dir(row, decision["official_doc_type"])
        target_dir.mkdir(parents=True, exist_ok=True)

        target_pdf_path = target_dir / "document.pdf"
        target_manifest_path = target_dir / "manifest.json"
        target_references_path = target_dir / "references.json"

        status = "copied"
        if target_pdf_path.exists():
            existing_sha256 = self.compute_sha256(target_pdf_path)
            if existing_sha256 != expected_sha256:
                raise ValueError(
                    f"document.pdf existe deja avec un SHA-256 different : "
                    f"{target_pdf_path}"
                )
            status = "already_exists"
        else:
            shutil.copy2(source_path, target_pdf_path)
            copied_sha256 = self.compute_sha256(target_pdf_path)
            if copied_sha256 != expected_sha256:
                target_pdf_path.unlink(missing_ok=True)
                raise ValueError(
                    f"Copie invalide : {copied_sha256} != {expected_sha256}"
                )

        target_manifest_path.write_text(
            json.dumps(
                self.build_manifest(row, decision, source_path, target_pdf_path),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        target_references_path.write_text(
            json.dumps(
                context.get("references_payload")
                or self.build_fallback_references(row),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return status

    def build_manifest(
        self,
        row: pd.Series,
        decision: dict,
        source_path: Path,
        target_pdf_path: Path,
    ) -> dict:
        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "technical_document_family": self.safe_value(row.get("document_family")),
            "official_doc_type": decision["official_doc_type"],
            "official_doc_type_label": decision["official_doc_type_label"],
            "doc_type_stratum": decision["doc_type_stratum"],
            "doc_subtype": decision["doc_subtype"],
            "period_type": decision["period_type"],
            "regulatory_status": decision["regulatory_status"],
            "parent_doc_id": decision["parent_doc_id"],
            "taxonomy_notes": decision["notes"],
            "original_organized_local_path": str(source_path),
            "taxonomy_organized_local_path": str(target_pdf_path.resolve()),
            "organization_created_at": self.utc_now(),
        }

    def build_target_dir(self, row: pd.Series, official_doc_type: str) -> Path:
        company_slug = self.slugify(
            self.safe_value(row.get("company_slug"))
            or self.safe_value(row.get("company_name"))
            or "unknown_company"
        )
        year = str(self.safe_int_or_none(row.get("fiscal_year")) or "unknown_year")
        canonical_document_id = self.slugify(
            self.safe_value(row.get("canonical_document_id"))
            or str(row.get("sha256"))[:24]
        )
        return (
            self.output_corpus_root
            / company_slug
            / year
            / official_doc_type
            / canonical_document_id
        )

    def build_index_row(
        self,
        row: pd.Series,
        decision: dict,
        status: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> dict:
        target_dir = None
        if decision.get("official_doc_type"):
            target_dir = self.build_target_dir(row, decision["official_doc_type"])

        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "technical_document_family": self.safe_value(row.get("document_family")),
            "official_doc_type": decision.get("official_doc_type"),
            "official_doc_type_label": decision.get("official_doc_type_label"),
            "doc_type_stratum": decision.get("doc_type_stratum"),
            "doc_subtype": decision.get("doc_subtype"),
            "period_type": decision.get("period_type"),
            "regulatory_status": decision.get("regulatory_status"),
            "parent_doc_id": decision.get("parent_doc_id"),
            "status": status,
            "taxonomy_notes": json.dumps(decision.get("notes") or [], ensure_ascii=False),
            "source_document_path": self.safe_value(row.get("organized_document_path")),
            "taxonomy_document_path": str((target_dir / "document.pdf").resolve())
            if target_dir
            else None,
            "taxonomy_manifest_path": str((target_dir / "manifest.json").resolve())
            if target_dir
            else None,
            "taxonomy_references_path": str((target_dir / "references.json").resolve())
            if target_dir
            else None,
            "error_type": error_type,
            "error_message": error_message,
        }

    def load_context(self, row: pd.Series) -> dict:
        manifest_payload = self.load_json(row.get("organized_manifest_path"))
        references_payload = self.load_json(row.get("organized_references_path"))
        return {
            "manifest_payload": manifest_payload,
            "references_payload": references_payload,
            "manifest_text": json.dumps(manifest_payload or {}, ensure_ascii=False),
            "references_text": json.dumps(references_payload or {}, ensure_ascii=False),
        }

    @staticmethod
    def load_json(path_value: Any):
        path_value = TaxonomyCorpusOrganizer.safe_value(path_value)
        if not path_value:
            return None
        path = Path(str(path_value))
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def build_fallback_references(row: pd.Series) -> dict:
        return {
            "canonical_document_id": TaxonomyCorpusOrganizer.safe_value(
                row.get("canonical_document_id")
            ),
            "sha256": TaxonomyCorpusOrganizer.safe_value(row.get("sha256")),
            "source_document_path": TaxonomyCorpusOrganizer.safe_value(
                row.get("organized_document_path")
            ),
            "source_manifest_path": TaxonomyCorpusOrganizer.safe_value(
                row.get("organized_manifest_path")
            ),
            "source_references_path": TaxonomyCorpusOrganizer.safe_value(
                row.get("organized_references_path")
            ),
        }

    @staticmethod
    def save_index(
        rows: list[dict],
        output_json_path: Path,
        output_csv_path: Path,
    ) -> None:
        output_json_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        pd.DataFrame(rows).to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def build_distribution(rows: list[dict]) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for row in rows:
            if row.get("status") not in {"copied", "already_exists"}:
                continue
            doc_type = row.get("official_doc_type")
            if not doc_type:
                continue
            distribution[doc_type] = distribution.get(doc_type, 0) + 1
        return dict(sorted(distribution.items()))

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> None:
        required = {
            "canonical_document_id",
            "sha256",
            "company_name",
            "company_slug",
            "fiscal_year",
            "document_family",
            "organized_document_path",
            "organized_manifest_path",
            "organized_references_path",
        }
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(
                "Colonnes absentes de l'index organise : " + ", ".join(missing)
            )

    @staticmethod
    def compute_sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def normalize_text(value: Any) -> str:
        text = str(value or "").lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def slugify(value: Any) -> str:
        text = TaxonomyCorpusOrganizer.normalize_text(value)
        text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        return text or "unknown"

    @staticmethod
    def safe_value(value: Any):
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        if str(value).strip() == "":
            return None
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @staticmethod
    def safe_int_or_none(value: Any) -> Optional[int]:
        value = TaxonomyCorpusOrganizer.safe_value(value)
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
