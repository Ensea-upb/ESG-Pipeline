# ESGVisualExtraction v1.0 - Release Notes

`ESGVisualExtraction` v1.0 is the first stable candidate-only visual extraction layer for figures, graphics, visual pages, and image-like objects detected by `ESGInformationExtraction`.

## Features

- Visual loader from `figure_index.jsonl`.
- Non-destructive crop generation or explicit crop fallback.
- Optional OCR with clean `ocr_unavailable` fallback.
- Rule-based visual classification.
- Candidate-only visual ESG rows.
- Visual audit findings and samples.
- Output contract and validator.

## Guarantees

- No PDF modification.
- No source output modification.
- No score.
- No validated ESG indicator.
- `review_required=true` for every candidate.
- `extraction_status=candidate_only` for every candidate.
- `confidence <= 0.5` for every visual candidate.

## Limits

- OCR is optional and may be unavailable.
- Placeholder crops may be used when PDF rendering is unavailable.
- Visual candidates are weak evidence until reviewed by a human.
