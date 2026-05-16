from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.config import DEFAULT_DICTIONARY_PATH
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.variable_mapper import map_records


def _record(key: str, label: str = "", family: str = "") -> dict[str, str]:
    return {
        "company": "LVMH",
        "fiscal_year": "2024",
        "document_id": "doc",
        "preparation_indicator_id": "prep",
        "indicator_key": key,
        "indicator_label": label,
        "indicator_family": family,
        "value_prepared": "1",
        "unit_prepared": "%",
        "quote": label,
    }


def test_maps_required_examples():
    cases = {
        "ghg_emissions_scope_1_2": "co2_emissions",
        "energy_consumption": "energy_consumption",
        "board_independence": "board_independence",
        "corruption": "corruption",
        "roe": "roe",
    }
    rows = map_records([_record(key) for key in cases], DEFAULT_DICTIONARY_PATH)
    assert [row["variable_name"] for row in rows] == list(cases.values())
    assert all(row["mapping_status"] == "mapped" for row in rows)


def test_unknown_stays_no_match_and_ambiguous_stays_ambiguous():
    rows = map_records([
        _record("unknown_metric", "unrelated metric"),
        _record("", "human rights and supply chain policy"),
    ], DEFAULT_DICTIONARY_PATH)

    assert rows[0]["mapping_status"] == "no_match"
    assert rows[1]["mapping_status"] == "ambiguous"
