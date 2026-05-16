from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_duplicates(path: Path) -> list[dict]:
    """
    Charge le fichier exact_duplicates.json.
    """

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def shorten(text: str | None, max_len: int = 120) -> str:
    """
    Raccourcit une chaîne pour un affichage lisible.
    """

    if text is None:
        return ""

    text = str(text).replace("\n", " ").strip()

    if len(text) <= max_len:
        return text

    return text[: max_len - 3] + "..."


def print_duplicate_group(group: dict, index: int) -> None:
    """
    Affiche un groupe de doublons exacts.
    """

    print("\n" + "=" * 100)
    print(f"GROUPE {index}")
    print("=" * 100)

    print(f"duplicate_group_id : {group.get('duplicate_group_id')}")
    print(f"sha256             : {group.get('sha256')}")
    print(f"duplicate_count   : {group.get('duplicate_count')}")
    print(f"companies         : {group.get('companies')}")
    print(f"document_families : {group.get('document_families')}")
    print(f"retrievers        : {group.get('retrievers')}")

    documents = group.get("documents") or []

    print("\nDocuments du groupe :")

    for i, doc in enumerate(documents, start=1):
        print("\n" + "-" * 80)
        print(f"Document {i}")
        print("-" * 80)

        print(f"document_id     : {doc.get('document_id')}")
        print(f"retriever       : {doc.get('retriever_name')}")
        print(f"family          : {doc.get('document_family')}")
        print(f"company         : {doc.get('company_name')}")
        print(f"fiscal_year     : {doc.get('fiscal_year')}")
        print(f"score           : {doc.get('score')}")
        print(f"decision        : {doc.get('decision')}")
        print(f"title           : {shorten(doc.get('source_title'))}")
        print(f"url             : {shorten(doc.get('source_url'), 160)}")
        print(f"local_path      : {doc.get('local_path')}")
        print(f"manifest_path   : {doc.get('manifest_path')}")


def print_summary(groups: list[dict]) -> None:
    """
    Affiche une synthèse compacte.
    """

    print("\n" + "=" * 100)
    print("SYNTHÈSE DES DOUBLONS EXACTS")
    print("=" * 100)

    print(f"Nombre de groupes de doublons : {len(groups)}")

    total_docs = sum(int(group.get("duplicate_count") or 0) for group in groups)
    print(f"Nombre total de documents dans ces groupes : {total_docs}")

    print("\nRésumé par groupe :")
    print("-" * 100)

    for group in groups:
        group_id = group.get("duplicate_group_id")
        count = group.get("duplicate_count")
        companies = ", ".join(group.get("companies") or [])
        families = ", ".join(group.get("document_families") or [])
        retrievers = ", ".join(group.get("retrievers") or [])

        print(
            f"{group_id} | count={count} | "
            f"companies={companies} | families={families} | retrievers={retrievers}"
        )


def main() -> None:
    duplicates_path = (
        PROJECT_ROOT
        / "data"
        / "deduplication"
        / "exact_duplicates.json"
    )

    groups = load_duplicates(duplicates_path)

    print_summary(groups)

    for index, group in enumerate(groups, start=1):
        print_duplicate_group(group, index)


if __name__ == "__main__":
    main()