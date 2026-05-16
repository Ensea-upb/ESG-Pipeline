from __future__ import annotations


def resolve_absence_status(text: str) -> str:
    normalized = str(text).strip().lower()
    if any(marker in normalized for marker in ("not disclosed", "non publie", "non publié", "not reported")):
        return "not_disclosed"
    return "missing_from_corpus"
