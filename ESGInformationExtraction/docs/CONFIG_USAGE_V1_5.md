# Config Usage v1.5

## extraction_config.yaml

Current role: configuration support. It documents intended extraction settings, but the active production behavior remains in `run_pdf_extraction.py`.

## section_taxonomy_v0.yaml

Current role: section taxonomy support. Some section concepts are also represented by hardcoded patterns in the active engine, so this file is not yet the only source of truth.

Risk: duplicated taxonomy logic can drift. A future refactor should make the taxonomy file the single source only after tests are updated.

## metric_catalog_v0.yaml

Current role: reserved for downstream ESG layers.

It must not be imported or used by `ESGInformationExtraction/run_pdf_extraction.py`. The documentary engine must not perform ESG semantic interpretation, metric validation, scoring, or indicator production.
