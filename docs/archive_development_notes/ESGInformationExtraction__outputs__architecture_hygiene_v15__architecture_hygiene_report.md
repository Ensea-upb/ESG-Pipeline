# Architecture Hygiene Report

## Active Engine
- run_pdf_extraction.py is the active production engine.
- line_count: 5614

## Potentially Orphan Modules
- parsing/ — exists=True used_by_run_pdf_extraction=False status=legacy_or_experimental
- section_detection/ — exists=True used_by_run_pdf_extraction=True status=active_or_referenced
- extraction/ — exists=True used_by_run_pdf_extraction=True status=active_or_referenced
- evidence/ — exists=True used_by_run_pdf_extraction=True status=active_or_referenced
- quality_control/ — exists=True used_by_run_pdf_extraction=False status=legacy_or_experimental
- document_base/ — exists=True used_by_run_pdf_extraction=False status=legacy_or_experimental

## Findings
- info | active_engine_identified | run_pdf_extraction.py identified as active production engine.
- minor | module_not_referenced_by_active_engine | parsing/ exists but is not referenced by run_pdf_extraction.py.
- minor | module_not_referenced_by_active_engine | quality_control/ exists but is not referenced by run_pdf_extraction.py.
- minor | module_not_referenced_by_active_engine | document_base/ exists but is not referenced by run_pdf_extraction.py.
