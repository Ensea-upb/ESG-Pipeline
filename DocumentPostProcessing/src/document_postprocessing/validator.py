from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pdfplumber

from .scope import filter_dataframe_scope


DOCUMENT_KEYWORDS = {
    "annual_report": [
        "annual report",
        "universal registration document",
        "document d'enregistrement universel",
        "rapport annuel",
        "integrated report",
    ],
    "sustainability_report": [
        "sustainability report",
        "esg report",
        "csr report",
        "rapport de durabilite",
        "rapport rse",
        "social and environmental responsibility",
    ],
    "climate_report": [
        "climate report",
        "tcfd",
        "transition plan",
        "net zero",
        "greenhouse gas",
        "emissions",
        "rapport climat",
        "plan de transition",
    ],
    "governance_report": [
        "corporate governance",
        "governance report",
        "board of directors",
        "gouvernement d'entreprise",
    ],
    "remuneration_report": [
        "remuneration report",
        "compensation report",
        "executive compensation",
        "rapport de remuneration",
    ],
    "vigilance_plan": [
        "vigilance plan",
        "duty of vigilance",
        "plan de vigilance",
        "human rights due diligence",
    ],
    "assurance_report": [
        "assurance report",
        "certification of sustainability information",
        "limited assurance",
        "reasonable assurance",
    ],
    "cdp_response": [
        "cdp",
        "climate change questionnaire",
        "water security questionnaire",
    ],
    "sbti_commitment": [
        "science based targets",
        "sbti",
        "near-term target",
        "net-zero target",
    ],
    "corporate_policy": [
        "policy",
        "code of conduct",
        "supplier code",
        "human rights policy",
        "anti-corruption policy",
    ],
    "agm_document": [
        "annual general meeting",
        "agm",
        "notice of meeting",
        "avis de convocation",
        "assemblee generale",
    ],
    "half_year_report": [
        "half-year report",
        "interim report",
        "rapport semestriel",
    ],
    "investor_presentation": [
        "investor presentation",
        "investor day",
        "presentation",
    ],
    "earnings_call": [
        "earnings call",
        "transcript",
        "conference call",
    ],
}


@dataclass
class DocumentValidationSummary:
    status: str
    message: str

    total_documents: int
    total_valid_pdf: int
    total_missing_file: int
    total_not_pdf: int
    total_unreadable_pdf: int
    total_likely_valid: int
    total_needs_review: int
    total_likely_wrong_company: int
    total_unreadable: int
    total_errors: int

    output_json_path: str
    output_csv_path: str
    summary_path: str
    errors: list[dict] = field(default_factory=list)


class DocumentValidator:
    """
    Validation documentaire offline du corpus organise.

    Cette classe ne fait pas d'OCR, ne contacte aucune API et ne modifie aucun
    PDF. Elle extrait uniquement le texte des trois premieres pages.
    """

    def __init__(
        self,
        organized_index_csv_path: str | Path = (
            "data/organized_corpus/organized_documents_index.csv"
        ),
        output_dir: str | Path = "data/validation",
        max_pages_to_extract: int = 3,
        text_sample_max_chars: int = 4000,
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.organized_index_csv_path = Path(organized_index_csv_path)
        self.output_dir = Path(output_dir)
        self.max_pages_to_extract = max_pages_to_extract
        self.text_sample_max_chars = text_sample_max_chars
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def validate(self) -> DocumentValidationSummary:
        if not self.organized_index_csv_path.exists():
            raise FileNotFoundError(
                f"Index de corpus organise introuvable : "
                f"{self.organized_index_csv_path}"
            )

        df = pd.read_csv(self.organized_index_csv_path)
        self.validate_columns(df)
        df = filter_dataframe_scope(df, self.company_slugs, self.years)

        results = []
        errors = []

        for _, row in df.iterrows():
            try:
                results.append(self.validate_row(row))
            except Exception as exc:
                error = {
                    "canonical_document_id": self.safe_value(
                        row.get("canonical_document_id")
                    ),
                    "sha256": self.safe_value(row.get("sha256")),
                    "error": str(exc),
                }
                errors.append(error)
                results.append(self.build_error_result(row, str(exc)))

        output_json_path = self.output_dir / "document_validation_results.json"
        output_csv_path = self.output_dir / "document_validation_results.csv"
        summary_path = self.output_dir / "document_validation_summary.json"

        self.save_results(results, output_json_path, output_csv_path)

        summary = self.build_summary(
            results=results,
            errors=errors,
            output_json_path=output_json_path,
            output_csv_path=output_csv_path,
            summary_path=summary_path,
        )

        summary_path.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return summary

    def validate_row(self, row: pd.Series) -> dict:
        organized_path = self.safe_value(row.get("organized_document_path"))
        file_path = Path(str(organized_path)) if organized_path else None

        notes: list[str] = []
        file_exists = bool(file_path and file_path.exists())
        is_pdf_header_valid = False
        file_size_mb = None
        page_count = None
        extraction_status = "not_attempted"
        extracted_text_sample = ""

        if not file_exists:
            technical_status = "missing_file"
            document_status = "unreadable"
            notes.append("Fichier organise introuvable.")
            return self.build_result(
                row=row,
                file_exists=file_exists,
                is_pdf_header_valid=is_pdf_header_valid,
                file_size_mb=file_size_mb,
                page_count=page_count,
                text_extraction_status=extraction_status,
                extracted_text_sample=extracted_text_sample,
                technical_validation_status=technical_status,
                document_validation_status=document_status,
                validation_notes=notes,
            )

        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 4)
        is_pdf_header_valid = self.has_pdf_header(file_path)

        if not is_pdf_header_valid:
            technical_status = "not_pdf"
            document_status = "unreadable"
            notes.append("Le fichier ne commence pas par %PDF-.")
            return self.build_result(
                row=row,
                file_exists=file_exists,
                is_pdf_header_valid=is_pdf_header_valid,
                file_size_mb=file_size_mb,
                page_count=page_count,
                text_extraction_status=extraction_status,
                extracted_text_sample=extracted_text_sample,
                technical_validation_status=technical_status,
                document_validation_status=document_status,
                validation_notes=notes,
            )

        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                extracted_text_sample = self.extract_text_sample(pdf)
                extraction_status = (
                    "success" if extracted_text_sample.strip() else "empty_text"
                )
        except Exception as exc:
            technical_status = "unreadable_pdf"
            document_status = "unreadable"
            notes.append(f"pdfplumber a echoue : {exc}")
            return self.build_result(
                row=row,
                file_exists=file_exists,
                is_pdf_header_valid=is_pdf_header_valid,
                file_size_mb=file_size_mb,
                page_count=page_count,
                text_extraction_status="pdfplumber_error",
                extracted_text_sample=extracted_text_sample,
                technical_validation_status=technical_status,
                document_validation_status=document_status,
                validation_notes=notes,
            )

        if page_count and page_count > 0:
            technical_status = "valid_pdf"
        else:
            technical_status = "needs_review"
            notes.append("PDF lisible mais nombre de pages nul ou indetermine.")

        document_status = self.compute_document_status(
            row=row,
            text=extracted_text_sample,
            technical_status=technical_status,
            notes=notes,
        )

        return self.build_result(
            row=row,
            file_exists=file_exists,
            is_pdf_header_valid=is_pdf_header_valid,
            file_size_mb=file_size_mb,
            page_count=page_count,
            text_extraction_status=extraction_status,
            extracted_text_sample=extracted_text_sample,
            technical_validation_status=technical_status,
            document_validation_status=document_status,
            validation_notes=notes,
        )

    def extract_text_sample(self, pdf) -> str:
        texts = []
        pages_to_extract = min(len(pdf.pages), self.max_pages_to_extract)

        for index in range(pages_to_extract):
            try:
                text = pdf.pages[index].extract_text() or ""
            except Exception:
                text = ""
            if text:
                texts.append(text)

        sample = "\n\n".join(texts).strip()
        return sample[: self.text_sample_max_chars]

    def compute_document_status(
        self,
        row: pd.Series,
        text: str,
        technical_status: str,
        notes: list[str],
    ) -> str:
        if technical_status in {"missing_file", "not_pdf", "unreadable_pdf"}:
            return "unreadable"

        normalized_text = self.normalize_text(text)
        if not normalized_text:
            notes.append("Aucun texte extrait sur les premieres pages.")
            return "needs_review"

        company_detected = self.company_detected(row, normalized_text)
        keywords = self.detect_keywords(row, normalized_text)
        years = self.detect_years(text)
        fiscal_year = self.safe_int_or_none(row.get("fiscal_year"))

        if not company_detected and len(normalized_text) > 500:
            notes.append("Nom de l'entreprise non detecte dans l'echantillon.")
            if keywords:
                return "needs_review"
            return "likely_wrong_company"

        if keywords:
            if fiscal_year and years and not ({fiscal_year, fiscal_year - 1} & set(years)):
                notes.append("Annees detectees eloignees de l'annee fiscale cible.")
                return "needs_review"
            return "likely_valid"

        notes.append("Aucun mot-cle documentaire specifique detecte.")
        return "needs_review"

    def build_result(
        self,
        row: pd.Series,
        file_exists: bool,
        is_pdf_header_valid: bool,
        file_size_mb: Optional[float],
        page_count: Optional[int],
        text_extraction_status: str,
        extracted_text_sample: str,
        technical_validation_status: str,
        document_validation_status: str,
        validation_notes: list[str],
    ) -> dict:
        detected_years = self.detect_years(extracted_text_sample)
        normalized_text = self.normalize_text(extracted_text_sample)

        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "document_family": self.safe_value(row.get("document_family")),
            "organized_local_path": self.safe_value(row.get("organized_document_path")),
            "manifest_path": self.safe_value(row.get("organized_manifest_path")),
            "references_path": self.safe_value(row.get("organized_references_path")),
            "file_exists": file_exists,
            "is_pdf_header_valid": is_pdf_header_valid,
            "file_size_mb": file_size_mb,
            "page_count": page_count,
            "text_extraction_status": text_extraction_status,
            "extracted_text_sample": extracted_text_sample,
            "detected_years": detected_years,
            "company_name_detected_in_text": self.company_detected(
                row,
                normalized_text,
            ),
            "probable_language": self.detect_language(normalized_text),
            "detected_document_keywords": self.detect_keywords(row, normalized_text),
            "technical_validation_status": technical_validation_status,
            "document_validation_status": document_validation_status,
            "validation_notes": validation_notes,
        }

    def build_error_result(self, row: pd.Series, message: str) -> dict:
        return self.build_result(
            row=row,
            file_exists=False,
            is_pdf_header_valid=False,
            file_size_mb=None,
            page_count=None,
            text_extraction_status="validation_error",
            extracted_text_sample="",
            technical_validation_status="needs_review",
            document_validation_status="unreadable",
            validation_notes=[message],
        )

    @staticmethod
    def has_pdf_header(path: Path) -> bool:
        try:
            with path.open("rb") as file:
                return file.read(5) == b"%PDF-"
        except OSError:
            return False

    def detect_keywords(self, row: pd.Series, normalized_text: str) -> list[str]:
        family = str(self.safe_value(row.get("document_family")) or "")
        keywords = DOCUMENT_KEYWORDS.get(family, [])
        detected = []

        for keyword in keywords:
            normalized_keyword = self.normalize_text(keyword)
            if normalized_keyword and normalized_keyword in normalized_text:
                detected.append(keyword)

        return detected

    @staticmethod
    def detect_years(text: str) -> list[int]:
        years = {
            int(match)
            for match in re.findall(r"\b(?:19|20)\d{2}\b", text or "")
            if 1900 <= int(match) <= 2099
        }
        return sorted(years)

    def company_detected(self, row: pd.Series, normalized_text: str) -> bool:
        company_name = self.normalize_text(self.safe_value(row.get("company_name")) or "")
        company_slug = self.normalize_text(self.safe_value(row.get("company_slug")) or "")

        candidates = [company_name, company_slug.replace("-", " ")]
        for candidate in candidates:
            candidate = candidate.strip()
            if len(candidate) >= 3 and candidate in normalized_text:
                return True

        return False

    @staticmethod
    def detect_language(normalized_text: str) -> str:
        if not normalized_text:
            return "unknown"

        french_markers = [
            " rapport ",
            " societe ",
            " conseil ",
            " assemblee ",
            " exercice ",
            " developpement durable ",
            " remuneration ",
        ]
        english_markers = [
            " report ",
            " company ",
            " board ",
            " directors ",
            " shareholders ",
            " sustainability ",
            " governance ",
        ]

        french_score = sum(marker in f" {normalized_text} " for marker in french_markers)
        english_score = sum(marker in f" {normalized_text} " for marker in english_markers)

        if french_score > english_score:
            return "fr"
        if english_score > french_score:
            return "en"
        return "unknown"

    @staticmethod
    def normalize_text(value: Any) -> str:
        text = str(value or "").lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> None:
        required_columns = {
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
        missing = sorted(required_columns - set(df.columns))
        if missing:
            raise ValueError(
                "Colonnes absentes de l'index organise : " + ", ".join(missing)
            )

    def build_summary(
        self,
        results: list[dict],
        errors: list[dict],
        output_json_path: Path,
        output_csv_path: Path,
        summary_path: Path,
    ) -> DocumentValidationSummary:
        total_valid_pdf = self.count_status(
            results,
            "technical_validation_status",
            "valid_pdf",
        )
        total_missing_file = self.count_status(
            results,
            "technical_validation_status",
            "missing_file",
        )
        total_not_pdf = self.count_status(
            results,
            "technical_validation_status",
            "not_pdf",
        )
        total_unreadable_pdf = self.count_status(
            results,
            "technical_validation_status",
            "unreadable_pdf",
        )
        total_likely_valid = self.count_status(
            results,
            "document_validation_status",
            "likely_valid",
        )
        total_needs_review = self.count_status(
            results,
            "document_validation_status",
            "needs_review",
        )
        total_likely_wrong_company = self.count_status(
            results,
            "document_validation_status",
            "likely_wrong_company",
        )
        total_unreadable = self.count_status(
            results,
            "document_validation_status",
            "unreadable",
        )

        status = "success" if not errors else "completed_with_errors"
        return DocumentValidationSummary(
            status=status,
            message=(
                f"Validation documentaire terminee : {total_valid_pdf} PDF(s) "
                f"techniquement valide(s), {total_likely_valid} document(s) "
                f"probablement valide(s), {total_needs_review} a revoir."
            ),
            total_documents=len(results),
            total_valid_pdf=total_valid_pdf,
            total_missing_file=total_missing_file,
            total_not_pdf=total_not_pdf,
            total_unreadable_pdf=total_unreadable_pdf,
            total_likely_valid=total_likely_valid,
            total_needs_review=total_needs_review,
            total_likely_wrong_company=total_likely_wrong_company,
            total_unreadable=total_unreadable,
            total_errors=len(errors),
            output_json_path=str(output_json_path),
            output_csv_path=str(output_csv_path),
            summary_path=str(summary_path),
            errors=errors,
        )

    @staticmethod
    def save_results(
        results: list[dict],
        output_json_path: Path,
        output_csv_path: Path,
    ) -> None:
        output_json_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        rows = []
        for result in results:
            row = result.copy()
            for key in ["detected_years", "detected_document_keywords", "validation_notes"]:
                row[key] = json.dumps(row.get(key) or [], ensure_ascii=False)
            rows.append(row)

        pd.DataFrame(rows).to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def count_status(results: list[dict], field_name: str, status: str) -> int:
        return sum(1 for result in results if result.get(field_name) == status)

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
        value = DocumentValidator.safe_value(value)
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
