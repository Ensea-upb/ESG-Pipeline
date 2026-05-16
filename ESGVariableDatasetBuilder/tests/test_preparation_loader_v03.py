from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.preparation_loader import (
    load_preparation_output,
    write_preparation_loading_outputs,
)

from .helpers import make_indicator_output, sample_rows


def test_loads_preparation_records_and_evidence(tmp_path):
    source = make_indicator_output(tmp_path, "db", sample_rows())
    loaded = load_preparation_output(source)

    assert len(loaded["records"]) == 2
    assert loaded["records"][0]["quote"]
    assert loaded["records"][0]["evidence_id"] == "ev_1"


def test_signals_final_indicator_and_score_rows(tmp_path):
    source = make_indicator_output(
        tmp_path,
        "db",
        [dict(sample_rows()[0], is_final_indicator="true"), dict(sample_rows()[1], score_produced="true")],
    )

    loaded = load_preparation_output(source)

    assert loaded["records"] == []
    assert {item["category"] for item in loaded["findings"]} == {"final_indicator_claim", "score_produced"}


def test_loading_outputs_are_written_for_empty_database(tmp_path):
    source = make_indicator_output(tmp_path, "db", [])
    output_dir = tmp_path / "out"
    loaded = load_preparation_output(source)
    write_preparation_loading_outputs(loaded, output_dir)

    assert (output_dir / "loaded_preparation_records.csv").exists()
    assert (output_dir / "preparation_loading_summary.json").exists()
