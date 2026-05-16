from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.dataset_builder import build_dataset
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.io_utils import read_csv, read_jsonl

from .helpers import make_indicator_output, sample_rows


def test_traceability_outputs_are_produced(tmp_path):
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    make_indicator_output(input_root, "db", sample_rows())

    build_dataset(input_root, output_dir, company="LVMH", year="2024", overwrite=True)

    long_rows = read_csv(output_dir / "esg_variables_long.csv")
    evidence_rows = read_csv(output_dir / "esg_variables_evidence.csv")
    missing_rows = read_csv(output_dir / "esg_variables_missing_report.csv")
    lineage_rows = read_jsonl(output_dir / "esg_variables_lineage.jsonl")

    assert len(long_rows) == 31
    assert any(row["variable_name"] == "co2_emissions" for row in evidence_rows)
    assert any(row["status"] == "missing_from_corpus" and row["reason"] for row in missing_rows)
    assert len(lineage_rows) == 31
