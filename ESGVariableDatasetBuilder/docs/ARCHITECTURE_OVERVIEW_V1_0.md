# Architecture Overview V1.0

Pipeline:

1. `input_discovery.py` scans preparation outputs.
2. `preparation_loader.py` loads preparation-only records.
3. `variable_mapper.py` maps indicators to final variables.
4. `value_selector.py` selects the safest status/value per variable.
5. `dataset_builder.py` writes the main and enriched datasets.
6. `evidence_builder.py` writes long, evidence, lineage, and missing outputs.
7. `quality_report.py` audits the resulting dataset.
8. `validators.py` enforces the stable contract.

All inputs are read-only. All generated artifacts are written to the requested
ESGVariableDatasetBuilder output directory.
