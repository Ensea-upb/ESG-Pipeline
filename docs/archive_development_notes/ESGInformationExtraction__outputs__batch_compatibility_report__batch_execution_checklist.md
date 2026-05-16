# Batch Execution Checklist

## Summary
- outputs_root: C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs
- contract_version: 1.0.0
- checklist_items_count: 26

## Important Safety Note
- Cette checklist n'execute aucune commande.
- Les commandes proposees doivent etre lancees manuellement.
- Aucune extraction ESG n'est realisee.
- Les outputs sources ne sont pas modifies par la generation de cette checklist.

## Execution Order
Follow the priority sections from 0 to 5. Within each section, follow `execution_order`.

## Priority 0 - No Action Needed
- [1] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test`
  - instruction: No manual remediation is needed.
  - command: `No command required.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`

## Priority 1 - Annotate Summary Only
- [2] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v08_lvmh_2024_sustainability_test`
  - instruction: Run the proposed annotation command manually if you want strict contract metadata.
  - command: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v08_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --annotate-summary`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v08_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`

## Priority 2 - Rerun Audit Standalone
- [3] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_example`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_example" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_example" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [4] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v041_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [5] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v042_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v042_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v042_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [6] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v04_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v04_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v04_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [7] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v051_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v051_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v051_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [8] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v052_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v052_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v052_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [9] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v061_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v061_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v061_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [10] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v06_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v06_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v06_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [11] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v07_lvmh_2024_sustainability_test`
  - instruction: Run the standalone audit command manually to regenerate audit files only.
  - command: `python ESGInformationExtraction/tools/run_document_audit.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v07_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v07_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`

## Priority 3 - Rerun Contract Validation
None.

## Priority 4 - Regenerate With Current Engine
- [12] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064251`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064251" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [13] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064721`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_064721" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [14] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065556`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065556" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [15] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065921`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_065921" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [16] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_070940`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_070940" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [17] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_071351`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_071351" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [18] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_112840`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `Regenerate this output with run_pdf_extraction.py using the original PDF path.`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\20260510_112840" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [19] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_bnp_paribas_2024_urd_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\bnp-paribas\2024\01_urd_annual_report\document.pdf" --document-id "bnp_paribas_2024_urd_v01_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_bnp_paribas_2024_urd_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_bnp_paribas_2024_urd_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [20] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v01_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v01_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [21] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v021_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v021_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v021_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v021_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [22] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v02_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v02_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v02_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v02_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [23] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v031_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v031_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v031_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v031_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [24] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v032_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v032_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v032_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v032_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [25] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v03_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v03_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v03_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v03_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`
- [26] `C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v0_lvmh_2024_sustainability_test`
  - instruction: Locate the original PDF and run the current PDF engine manually.
  - command: `python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" --document-id "lvmh_2024_sustainability_v0_test" --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v0_lvmh_2024_sustainability_test" --overwrite`
  - verification: `python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "C:\Users\hp\Desktop\ESG\ESGInformationExtraction\outputs\pdf_v0_lvmh_2024_sustainability_test" --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"`

## Priority 5 - Manual Review Required
None.

## Final Verification
Run the compatibility scanner again after manual remediation and confirm that no fragile output is marked as ready without review.
