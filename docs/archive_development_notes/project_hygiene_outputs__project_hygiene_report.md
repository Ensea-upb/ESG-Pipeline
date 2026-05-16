# Project Hygiene Audit

- Git repository: `False`
- Test helpers files: `7`
- Absolute helper imports: `0`
- Pyc files: `635`
- Legacy script suspects: `5`
- Unbounded requirements: `0`
- Retriever modules: `14`

## Findings

- **medium** `git` `.`: Project root is not a Git repository.
- **medium** `python_caches` `.`: Python cache artifacts detected: {'__pycache__': 223, '.pytest_cache': 1, '.pytest_tmp': 134, 'pyc_files': 635}
- **medium** `legacy_scripts` `run_extraction_test.py`: Legacy extraction-chain script suspected.
- **medium** `legacy_scripts` `ESGInformationExtraction/run_pdf_extraction.py`: Legacy extraction-chain script suspected.
- **medium** `legacy_scripts` `tools/project_hygiene_audit.py`: Legacy extraction-chain script suspected.
- **medium** `legacy_scripts` `ESGInformationExtraction/tools/audit_engine_architecture.py`: Legacy extraction-chain script suspected.
- **medium** `legacy_scripts` `ESGInformationExtraction/tools/batch_check_outputs.py`: Legacy extraction-chain script suspected.
- **medium** `retriever_tests` `AGMRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `AssuranceReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `CDPResponseRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `ClimateReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `CorporatePolicyRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `EarningsCallRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `GovernanceReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `HalfYearReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `InvestorPresentationRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `RemunerationReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `SBTiRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `SustainabilityReportRetriever`: Retriever has no non-empty tests.
- **medium** `retriever_tests` `VigilancePlanRetriever`: Retriever has no non-empty tests.
