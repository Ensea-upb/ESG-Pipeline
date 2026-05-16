from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.io_utils import read_csv
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.multi_company_year import build_multi_company_year_dataset

from .helpers import make_indicator_output, sample_rows


def test_multi_company_year_builds_global_dataset(tmp_path):
    input_root = tmp_path / "inputs"
    make_indicator_output(input_root, "lvmh", sample_rows())
    make_indicator_output(input_root, "acme", [dict(sample_rows()[0], company="ACME", document_id="doc_acme")])
    output_dir = tmp_path / "global"

    summary = build_multi_company_year_dataset(input_root, output_dir, overwrite=True)
    rows = read_csv(output_dir / "esg_variables_dataset.csv")

    assert summary["company_year_rows_count"] == 2
    assert len(rows) == 2
    assert (output_dir / "esg_variables_dataset_summary.json").exists()
