# ESGVariableDatasetBuilder Agent Delivery Report

## v0.1

- Created the module skeleton.
- Added the official 31-variable dictionary.
- Documented corpus-only policy for ESG, controversy, and financial variables.
- No scoring fields or external sources are declared.

## v0.2

- Added input discovery for ESGIndicatorDatabase preparation outputs.
- Added company x year grouping with multi-document support.
- Added inventory, sources JSONL, and discovery summary outputs.

## v0.3

- Added preparation database loader for records, evidence links, and lineage.
- Enforced preparation-only loading and reported final-indicator/score claims.
- Added empty database handling as a warning path.

## v0.4

- Added dictionary-based indicator-to-variable mapping.
- Mapping uses indicator key, family, label, and dictionary keywords.
- Ambiguous and no-match candidates are preserved without forced mapping.

## v0.5

- Added best-value selection per company x year x variable.
- Added statuses for found, missing_from_corpus, qualitative_only, needs_review, and conflicting_values.
- Conflicting numeric values are not arbitrarily selected.

## v0.6

- Added `esg_variables_dataset.csv` with one row per company x year.
- Added `esg_variables_dataset_enriched.csv` with value, unit, status, source document, page, and confidence metadata.

## v0.7

- Added long dataset, evidence CSV, lineage JSONL, and missing report outputs.
- Found values require traceable evidence in validation and quality checks.

## v0.8

- Added quality report JSON, JSONL findings, and Markdown summary.
- Added checks for found-without-evidence, score detection, external-source detection, and status counts.

## v0.9

- Added stable dataset contract and validation CLI.
- Validator checks required files, variables, statuses, duplicate company-year rows, score columns, external sources, and found evidence.

## v1.0

- Added multi-company-year runner.
- Added release and architecture documentation.
- ESGVariableDatasetBuilder tests pass locally.
