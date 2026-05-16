# Dataset Guide V1.0

`esg_variables_dataset.csv` is the compact analyst-facing table. Missing
variables are blank in this file.

`esg_variables_dataset_enriched.csv` carries the status and evidence metadata
needed to interpret blanks and non-final values.

`esg_variables_long.csv` is the normalized version with one row per company,
year, and variable.

`esg_variables_evidence.csv` records the PDF-derived evidence for selected
values. `esg_variables_missing_report.csv` explains absent or incomplete
variables.

Variables are never filled from external sources. Financial variables and
controversies are searched only in the available PDF-derived corpus outputs.
