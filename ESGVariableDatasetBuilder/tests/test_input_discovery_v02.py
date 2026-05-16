from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.input_discovery import (
    discover_inputs,
    group_company_year,
    write_input_discovery_outputs,
)

from .helpers import make_indicator_output, sample_rows


def test_discovers_and_groups_company_year(tmp_path):
    root = tmp_path / "inputs"
    make_indicator_output(root, "lvmh_a", sample_rows())
    make_indicator_output(root, "lvmh_b", [dict(sample_rows()[0], document_id="doc_other")])

    sources = discover_inputs(root)
    inventory = group_company_year(sources)

    assert len(sources) == 2
    assert len(inventory) == 1
    assert inventory[0]["company"] == "LVMH"
    assert inventory[0]["year"] == "2024"
    assert sorted(inventory[0]["document_ids"]) == ["doc_lvmh_2024", "doc_other"]


def test_discovery_writes_reports_and_handles_empty_database(tmp_path):
    root = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    make_indicator_output(root, "empty_lvmh_2024", [])

    result = write_input_discovery_outputs(root, output_dir)

    assert result["summary"]["sources_count"] == 1
    assert (output_dir / "company_year_input_inventory.json").exists()
    assert (output_dir / "company_year_input_sources.jsonl").exists()
    assert (output_dir / "input_discovery_summary.json").exists()
