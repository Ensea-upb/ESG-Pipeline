from __future__ import annotations

from pathlib import Path

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.variable_dictionary import FINAL_VARIABLES, load_variable_dictionary


ROOT = Path(__file__).resolve().parents[2]


def test_dictionary_exists_and_contains_31_variables() -> None:
    path = ROOT / "ESGVariableDatasetBuilder" / "config" / "esg_variable_dictionary_v0.yaml"
    assert path.exists()
    variables = load_variable_dictionary(path)
    names = [item["variable_name"] for item in variables]
    assert names == FINAL_VARIABLES
    assert len(names) == 31


def test_dictionary_required_fields_and_no_score_weight() -> None:
    variables = load_variable_dictionary(ROOT / "ESGVariableDatasetBuilder" / "config" / "esg_variable_dictionary_v0.yaml")
    for item in variables:
        assert item["definition"]
        assert item["missing_rule"]
        assert "score_weight" not in item
    text = (ROOT / "ESGVariableDatasetBuilder" / "config" / "esg_variable_dictionary_v0.yaml").read_text(encoding="utf-8")
    assert "external_source_url" not in text
