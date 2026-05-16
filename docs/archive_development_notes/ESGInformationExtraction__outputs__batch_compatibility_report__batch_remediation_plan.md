# Batch Remediation Plan

Ce plan ne modifie aucun output. Il recommande uniquement les actions minimales a effectuer.

## Summary
- outputs_root: C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs
- contract_version: 1.0.0
- outputs_scanned_count: 26

## Actions Distribution
- annotate_summary_only: 1
- no_action_needed: 1
- regenerate_with_current_engine: 15
- rerun_audit_standalone: 9

## No Action Needed
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test`: Output is compatible with contract v1.0.

## Annotate Summary Only
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v08_lvmh_2024_sustainability_test`: Only engine_contract_version appears to be missing from extraction_summary.json.
  - command: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v08_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --annotate-summary`

## Rerun Audit Standalone
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_example`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_example" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v042_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v042_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v04_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v04_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v051_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v051_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v052_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v052_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v061_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v061_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v06_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v06_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v07_lvmh_2024_sustainability_test`: Core documentary files exist, but audit outputs are missing.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v07_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`

## Regenerate With Current Engine
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064251`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064721`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065556`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065921`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_070940`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_071351`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_112840`: One or more core documentary files are missing: text_blocks.jsonl.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_bnp_paribas_2024_urd_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\bnp-paribas\2024\01_urd_annual_report\document.pdf" --document-id "bnp_paribas_2024_urd_v01_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_bnp_paribas_2024_urd_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v01_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v021_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v021_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v021_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v02_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v02_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v02_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v031_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v031_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v031_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v032_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v032_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v032_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v03_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v03_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v03_lvmh_2024_sustainability_test" --overwrite`
- `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v0_lvmh_2024_sustainability_test`: One or more core documentary files are missing: evidence_store.jsonl.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v0_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v0_lvmh_2024_sustainability_test" --overwrite`

## Manual Review Required
None.

## Recommended Execution Order
1. Run no automatic command for `no_action_needed` outputs.
2. Annotate summaries for low-risk compatibility warnings if desired.
3. Regenerate standalone audits for `migration_required` outputs with intact core files.
4. Regenerate incompatible outputs only after confirming the original PDF path.
5. Review ambiguous outputs manually before any destructive or expensive operation.

## Limitations
The remediation plan is advisory. It does not execute commands, repair outputs, parse PDFs, or perform ESG extraction.
