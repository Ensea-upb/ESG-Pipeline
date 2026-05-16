from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.dataset_builder import build_dataset
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.io_utils import read_csv
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.variable_dictionary import FINAL_VARIABLES

from .helpers import make_indicator_output, sample_rows


def test_builds_main_and_enriched_dataset(tmp_path):
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    make_indicator_output(input_root, "db", sample_rows())

    build_dataset(input_root, output_dir, company="LVMH", year="2024", overwrite=True)

    main = read_csv(output_dir / "esg_variables_dataset.csv")
    enriched = read_csv(output_dir / "esg_variables_dataset_enriched.csv")
    assert len(main) == 1
    assert set(["company", "year", *FINAL_VARIABLES]).issubset(main[0].keys())
    assert main[0]["co2_emissions"] == "12.5"
    assert main[0]["waste"] == ""
    assert enriched[0]["waste_status"] == "missing_from_corpus"
