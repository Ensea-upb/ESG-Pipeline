# Onyxia Local Integration Status

Source report: `onyxia_cac40_5y_full_20260510_085527`

## Integrated

- `audit_selected_documents.py` is now part of the configured post-processing chain.
- Run-isolated defaults are supported through `ESG_POSTPROCESS_OUTPUT_ROOT`.
- The audit writes:
  - `selected_documents_quality_audit_v2.csv`
  - `selected_documents_clean_likely_valid_v2.csv`
  - `selected_documents_to_review_v2.csv`
  - `selected_documents_quarantine_v2.csv`
  - `extraction_index_strict_likely_valid.csv`
  - `extraction_index_usable_excluding_quarantine.csv`
  - `exclusion_index_quarantine_wrong_company.csv`
  - `quality_summary_by_company.csv`
  - `quality_summary_by_doc_type.csv`
  - `quality_audit_report.md`
  - `audit_summary.json`
- Markdown generation is internal and does not require `tabulate`.
- `final_path` existence is checked and summarized.
- The rule "do not use raw ESGFinalCorpus directly" is documented.

## Validated

- `python -m compileall -q DocumentPostProcessing ESGOrchestrator`: passed
- `python -m pytest DocumentPostProcessing/tests ESGOrchestrator/tests`: 2 passed
- `python -m pytest --basetemp .pytest_tmp/global_onyxia_audit`: 406 passed
- `python tools/run_project_validation.py --project-root . --full`: passed

## Remaining Engineering Work

- Add disk-space preflight before large copy/materialization steps.
- Add `copy_mode = copy | hardlink | symlink` across corpus organizers and final selection.
- Reduce physical PDF duplication in large Onyxia-scale runs.
- Harden retrievers that fail on non-HTML or binary content.
- Improve company-document validation for short policy documents.
