from __future__ import annotations

import csv

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.config import DEFAULT_CONTRACT_PATH, DEFAULT_DICTIONARY_PATH
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.dataset_builder import build_dataset
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.validators import validate_dataset

from .helpers import make_indicator_output, sample_rows


def test_contract_accepts_valid_dataset(tmp_path):
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    make_indicator_output(input_root, "db", sample_rows())
    build_dataset(input_root, output_dir, company="LVMH", year="2024", overwrite=True)

    result = validate_dataset(output_dir, DEFAULT_CONTRACT_PATH, DEFAULT_DICTIONARY_PATH)

    assert result["status"] == "passed"


def test_contract_fails_missing_variable_invalid_status_and_duplicate(tmp_path):
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    make_indicator_output(input_root, "db", sample_rows())
    build_dataset(input_root, output_dir, company="LVMH", year="2024", overwrite=True)

    dataset_path = output_dir / "esg_variables_dataset.csv"
    rows = list(csv.DictReader(dataset_path.open("r", encoding="utf-8")))
    fieldnames = [field for field in rows[0].keys() if field != "waste"]
    with dataset_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({field: rows[0][field] for field in fieldnames})
        writer.writerow({field: rows[0][field] for field in fieldnames})

    long_path = output_dir / "esg_variables_long.csv"
    long_rows = list(csv.DictReader(long_path.open("r", encoding="utf-8")))
    long_rows[0]["status"] = "bad_status"
    with long_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=long_rows[0].keys())
        writer.writeheader()
        writer.writerows(long_rows)

    result = validate_dataset(output_dir, DEFAULT_CONTRACT_PATH, DEFAULT_DICTIONARY_PATH)

    assert result["status"] == "failed"
    assert any("missing_column:waste" == error for error in result["errors"])
    assert any(error.startswith("invalid_status") for error in result["errors"])
    assert any(error.startswith("duplicate_company_year") for error in result["errors"])
