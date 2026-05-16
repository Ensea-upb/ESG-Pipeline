# ESGIndicatorValidation v1.0 - Release Notes

This release creates a conservative ESG pre-validation layer after `ESGExtractionOrchestrator`.

Main capabilities:

- loads consolidated ESG candidates;
- assigns pre-validation statuses;
- normalizes values, units and years without validating them;
- maps candidates to cautious ESG families;
- groups duplicates without silent deletion;
- builds a human review queue;
- produces audit and contract validation outputs.

Non-goals:

- no validated ESG indicator;
- no ESG score;
- no final metric;
- no LLM, RAG or OCR.
