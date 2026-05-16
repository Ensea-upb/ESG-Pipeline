from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.value_selector import select_values


def _candidate(value: str, variable: str = "co2_emissions", quote: str = "quote") -> dict[str, str]:
    return {
        "company": "LVMH",
        "year": "2024",
        "variable_name": variable,
        "mapping_status": "mapped",
        "value_prepared": value,
        "unit_prepared": "tCO2e",
        "document_id": "doc",
        "page_number": "1",
        "quote": quote,
        "mapping_confidence": "1.0",
        "preparation_indicator_id": "prep",
        "evidence_id": "ev",
    }


def test_selects_found_value_and_marks_missing():
    selected = select_values([_candidate("10")], [("LVMH", "2024")])
    co2 = next(row for row in selected if row["variable_name"] == "co2_emissions")
    waste = next(row for row in selected if row["variable_name"] == "waste")

    assert co2["selected_status"] == "found"
    assert co2["selected_value"] == "10"
    assert waste["selected_status"] == "missing_from_corpus"


def test_detects_conflicting_values_without_arbitrary_choice():
    selected = select_values([_candidate("10"), _candidate("11")], [("LVMH", "2024")])
    co2 = next(row for row in selected if row["variable_name"] == "co2_emissions")

    assert co2["selected_status"] == "conflicting_values"
    assert co2["selected_value"] == ""


def test_qualitative_only_when_quote_without_numeric_value():
    selected = select_values([_candidate("", variable="biodiversity", quote="Biodiversity policy exists.")], [("LVMH", "2024")])
    row = next(item for item in selected if item["variable_name"] == "biodiversity")

    assert row["selected_status"] == "qualitative_only"


def test_selects_accepted_candidate_before_other_numeric_candidate():
    low_priority = _candidate("10")
    accepted = _candidate("10")
    accepted["decision_reason"] = "accept_candidate"
    accepted["cell_id"] = "cell_accepted"

    selected = select_values([low_priority, accepted], [("LVMH", "2024")])
    row = next(item for item in selected if item["variable_name"] == "co2_emissions")

    assert row["cell_id"] == "cell_accepted"
