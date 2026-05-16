# Legacy Scripts

`ESGInformationExtraction/run_pdf_extraction.py` is the active
ESGInformationExtraction v1.x document engine.

`run_extraction_test.py` is kept as a legacy/manual experiment around an older
chain:

- `document_base`
- `parsing`
- `section_detection`
- `extraction`
- `evidence`

Those folders should not be treated as the active v1.x production pipeline by
future agents. They may still be useful for historical context, but new
validation, extraction, and contract work should use the v1.x CLIs documented
under `ESGInformationExtraction/docs/`.

Do not move or delete `run_extraction_test.py` without first checking local
automation that may still reference the path. The current hygiene pass only
adds an explicit warning and this documentation.
