from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .scope import filter_dataframe_scope


@dataclass
class CorpusOrganizationResult:
    status: str
    message: str

    total_canonical_documents: int
    total_document_family_copies_planned: int
    total_copied_files: int
    total_existing_files: int
    total_missing_files: int
    total_errors: int

    output_corpus_root: str
    output_index_csv_path: str
    output_index_json_path: str
    summary_path: str

    errors: list[dict] = field(default_factory=list)


class CorpusOrganizer:
    """
    Organise le registre canonique en corpus lisible humainement.

    Les PDF originaux ne sont jamais modifies ni deplaces. Les documents sont
    copies vers ESGCorpus, une fois par famille documentaire detectee.
    """

    def __init__(
        self,
        canonical_csv_path: str | Path = "data/deduplication/canonical_documents.csv",
        output_corpus_root: str | Path = "../ESGCorpus",
        output_dir: str | Path = "data/organized_corpus",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.canonical_csv_path = Path(canonical_csv_path)
        self.output_corpus_root = Path(output_corpus_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def organize(self) -> CorpusOrganizationResult:
        if not self.canonical_csv_path.exists():
            raise FileNotFoundError(
                f"Registre canonique introuvable : {self.canonical_csv_path}"
            )

        df = pd.read_csv(self.canonical_csv_path)
        self.validate_columns(df)
        df = filter_dataframe_scope(df, self.company_slugs, self.years)

        self.output_corpus_root.mkdir(parents=True, exist_ok=True)

        index_rows: list[dict] = []
        errors: list[dict] = []
        total_planned = 0
        total_copied = 0
        total_existing = 0
        total_missing = 0

        for _, row in df.iterrows():
            families = self.get_document_families(row)
            total_planned += len(families)

            source_path_value = self.safe_value(row.get("canonical_local_path"))
            if source_path_value is None:
                error = self.build_error(row, "missing_canonical_local_path")
                errors.append(error)
                for family in families:
                    index_rows.append(
                        self.build_index_row(row, family, status="error", error=error)
                    )
                continue

            source_path = Path(str(source_path_value))
            if not source_path.exists():
                total_missing += len(families)
                error = self.build_error(
                    row,
                    "missing_file",
                    message=f"Fichier source introuvable : {source_path}",
                )
                for family in families:
                    index_rows.append(
                        self.build_index_row(
                            row,
                            family,
                            status="missing_file",
                            error=error,
                        )
                    )
                continue

            expected_sha256 = str(row.get("sha256"))
            actual_source_sha256 = self.compute_sha256(source_path)
            if actual_source_sha256 != expected_sha256:
                error = self.build_error(
                    row,
                    "source_sha256_mismatch",
                    message=(
                        f"SHA-256 source inattendu pour {source_path}: "
                        f"{actual_source_sha256} != {expected_sha256}"
                    ),
                )
                errors.append(error)
                for family in families:
                    index_rows.append(
                        self.build_index_row(row, family, status="error", error=error)
                    )
                continue

            for family in families:
                try:
                    status = self.organize_family_copy(
                        row=row,
                        document_family=family,
                        source_path=source_path,
                        expected_sha256=expected_sha256,
                    )

                    if status == "copied":
                        total_copied += 1
                    elif status == "already_exists":
                        total_existing += 1

                    index_rows.append(
                        self.build_index_row(row, family, status=status)
                    )

                except Exception as exc:
                    error = self.build_error(row, "copy_error", message=str(exc))
                    errors.append(error)
                    index_rows.append(
                        self.build_index_row(row, family, status="error", error=error)
                    )

        output_index_json_path = self.output_dir / "organized_documents_index.json"
        output_index_csv_path = self.output_dir / "organized_documents_index.csv"
        summary_path = self.output_dir / "corpus_organization_summary.json"

        self.save_index(index_rows, output_index_json_path, output_index_csv_path)

        status = "success" if not errors else "completed_with_errors"
        result = CorpusOrganizationResult(
            status=status,
            message=(
                f"Organisation du corpus terminee : {total_copied} copie(s) "
                f"creee(s), {total_existing} fichier(s) deja present(s), "
                f"{total_missing} fichier(s) source manquant(s), {len(errors)} erreur(s)."
            ),
            total_canonical_documents=len(df),
            total_document_family_copies_planned=total_planned,
            total_copied_files=total_copied,
            total_existing_files=total_existing,
            total_missing_files=total_missing,
            total_errors=len(errors),
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

    def organize_family_copy(
        self,
        row: pd.Series,
        document_family: str,
        source_path: Path,
        expected_sha256: str,
    ) -> str:
        target_dir = self.build_target_dir(row, document_family)
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
                    f"Copie invalide pour {target_pdf_path}: "
                    f"{copied_sha256} != {expected_sha256}"
                )

        target_manifest_path.write_text(
            json.dumps(
                self.build_manifest(row, document_family, source_path, target_pdf_path),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        target_references_path.write_text(
            json.dumps(
                self.build_references(row),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return status

    def build_target_dir(self, row: pd.Series, document_family: str) -> Path:
        company_slug = self.slugify(
            self.safe_value(row.get("company_slug"))
            or self.safe_value(row.get("company_name"))
            or "unknown_company"
        )
        fiscal_year = self.safe_int_or_unknown(row.get("fiscal_year"))
        family_slug = self.slugify(document_family or "unknown_family")
        canonical_document_id = self.slugify(
            self.safe_value(row.get("canonical_document_id"))
            or str(row.get("sha256"))[:24]
        )

        return (
            self.output_corpus_root
            / company_slug
            / fiscal_year
            / family_slug
            / canonical_document_id
        )

    def build_manifest(
        self,
        row: pd.Series,
        document_family: str,
        source_path: Path,
        target_pdf_path: Path,
    ) -> dict:
        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "document_family": document_family,
            "document_families_detected": self.get_document_families(row),
            "retrievers_detected": self.parse_json_list(row.get("retrievers_detected")),
            "canonical_source_title": self.safe_value(
                row.get("canonical_source_title")
            ),
            "canonical_source_url": self.safe_value(row.get("canonical_source_url")),
            "original_local_path": str(source_path),
            "organized_local_path": str(target_pdf_path.resolve()),
            "duplicate_count": self.safe_int_or_none(row.get("duplicate_count")),
            "is_duplicate_group": self.safe_bool(row.get("is_duplicate_group")),
            "organization_created_at": self.utc_now(),
        }

    def build_references(self, row: pd.Series) -> dict:
        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "all_references": self.parse_json_list(row.get("all_references")),
        }

    def build_index_row(
        self,
        row: pd.Series,
        document_family: str,
        status: str,
        error: Optional[dict] = None,
    ) -> dict:
        target_dir = self.build_target_dir(row, document_family)

        return {
            "canonical_document_id": self.safe_value(row.get("canonical_document_id")),
            "sha256": self.safe_value(row.get("sha256")),
            "company_name": self.safe_value(row.get("company_name")),
            "company_slug": self.safe_value(row.get("company_slug")),
            "fiscal_year": self.safe_int_or_none(row.get("fiscal_year")),
            "document_family": document_family,
            "status": status,
            "source_path": self.safe_value(row.get("canonical_local_path")),
            "organized_document_path": str((target_dir / "document.pdf").resolve()),
            "organized_manifest_path": str((target_dir / "manifest.json").resolve()),
            "organized_references_path": str((target_dir / "references.json").resolve()),
            "duplicate_count": self.safe_int_or_none(row.get("duplicate_count")),
            "is_duplicate_group": self.safe_bool(row.get("is_duplicate_group")),
            "error_type": error.get("error_type") if error else None,
            "error_message": error.get("message") if error else None,
        }

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> None:
        required_columns = {
            "canonical_document_id",
            "sha256",
            "company_name",
            "company_slug",
            "fiscal_year",
            "canonical_document_family",
            "canonical_local_path",
            "canonical_source_url",
            "canonical_source_title",
            "document_families_detected",
            "retrievers_detected",
            "duplicate_count",
            "is_duplicate_group",
            "all_references",
        }
        missing = sorted(required_columns - set(df.columns))
        if missing:
            raise ValueError(
                "Colonnes absentes du registre canonique : " + ", ".join(missing)
            )

    def get_document_families(self, row: pd.Series) -> list[str]:
        families = self.parse_json_list(row.get("document_families_detected"))
        families = [str(family) for family in families if self.has_value(family)]

        if not families:
            fallback = self.safe_value(row.get("canonical_document_family"))
            if fallback:
                families = [str(fallback)]

        if not families:
            families = ["unknown_family"]

        return self.unique_values(families)

    @staticmethod
    def parse_json_list(value: Any) -> list:
        if not CorpusOrganizer.has_value(value):
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
    def build_error(
        row: pd.Series,
        error_type: str,
        message: Optional[str] = None,
    ) -> dict:
        return {
            "canonical_document_id": CorpusOrganizer.safe_value(
                row.get("canonical_document_id")
            ),
            "sha256": CorpusOrganizer.safe_value(row.get("sha256")),
            "error_type": error_type,
            "message": message or error_type,
        }

    @staticmethod
    def compute_sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def unique_values(values: list[Any]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if not CorpusOrganizer.has_value(value):
                continue
            text = str(value)
            if text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def slugify(value: Any) -> str:
        text = str(value or "").lower().strip()
        chars = []
        previous_dash = False

        for char in text:
            if char.isalnum():
                chars.append(char)
                previous_dash = False
            else:
                if not previous_dash:
                    chars.append("-")
                    previous_dash = True

        slug = "".join(chars).strip("-")
        return slug or "unknown"

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
        if not CorpusOrganizer.has_value(value):
            return None
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @staticmethod
    def safe_int_or_none(value: Any) -> Optional[int]:
        if not CorpusOrganizer.has_value(value):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_int_or_unknown(value: Any) -> str:
        parsed = CorpusOrganizer.safe_int_or_none(value)
        if parsed is None:
            return "unknown_year"
        return str(parsed)

    @staticmethod
    def safe_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if not CorpusOrganizer.has_value(value):
            return False
        return str(value).strip().lower() in {"true", "1", "yes", "y"}

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
