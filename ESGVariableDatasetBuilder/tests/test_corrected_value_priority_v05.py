from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.config import DEFAULT_DICTIONARY_PATH
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.variable_mapper import map_records


def test_mapper_uses_corrected_value_before_prepared_and_raw():
    rows = map_records(
        [
            {
                "company": "LVMH",
                "fiscal_year": "2024",
                "document_id": "doc",
                "preparation_indicator_id": "prep",
                "indicator_key": "co2_emissions",
                "indicator_label": "GHG emissions",
                "corrected_value": "42",
                "value_prepared": "10",
                "value_raw": "raw 1",
                "unit_prepared": "tCO2e",
                "quote": "GHG emissions",
            }
        ],
        DEFAULT_DICTIONARY_PATH,
    )

    assert rows[0]["value_prepared"] == "42"
