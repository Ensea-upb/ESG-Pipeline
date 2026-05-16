# ESGCSVExtraction v1.0 - Release Notes

## Summary

`ESGCSVExtraction` v1.0 is the first stable candidate-only CSV layer built on top of `ESGInformationExtraction` documentary outputs. It transforms multimodal documentary evidence into auditable ESG information candidates without validating indicators or producing scores.

## Main Features

- Global ESG candidate CSV and JSONL export.
- Typed CSV exports for observed metrics, targets, policies, risks, boundary contexts, methodology contexts, and visual evidence.
- Candidate auto-audit with findings and samples.
- Multi-document audit over existing `ESGInformationExtraction` output folders.
- Stable CSV output contract and CLI validator.

## Produced Files

- `esg_information_candidates.csv`
- `esg_information_candidates.jsonl`
- `observed_metrics.csv`
- `targets.csv`
- `policies.csv`
- `risks.csv`
- `boundary_contexts.csv`
- `methodology_contexts.csv`
- `visual_evidences.csv`
- `extraction_audit.csv`
- `candidate_audit_summary.json`
- `candidate_audit_findings.jsonl`
- `candidate_audit_samples.csv`
- `extraction_summary.json`

## Guarantees

- Candidate-only outputs.
- `review_required=true` for every row.
- `extraction_status=candidate_only` for every row.
- `confidence <= 0.6`.
- No ESG score, validated indicator, RAG, LLM, OCR, or PDF parsing.
- No modification of `ESGInformationExtraction`, PDFs, manifests, or documentary output inputs.

## Remaining Limits

- Rules are conservative and heuristic.
- Some candidates may be false positives.
- Real-world diversity testing remains limited by the available local outputs.
- Tables and figures are only treated as documentary evidence, not interpreted.

## Not Included

- ESG validation.
- Regulatory compliance determination.
- Metric normalization as final data.
- Company scoring.
- Automated reporting decisions.
