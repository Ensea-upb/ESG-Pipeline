# ADR-002 — Schema and Architecture Hygiene v1.5

## Status

Accepted.

## Decision

`run_pdf_extraction.py` remains the source of truth for the active PDF documentary engine in the short term.

The visible package directories such as `parsing/`, `evidence/`, `section_detection/`, `quality_control/`, and `document_base/` are not removed in v1.5. They are documented as legacy, experimental, or reserved until a deliberate refactor is planned.

## Rationale

The engine has a stable output contract and a large regression suite. A heavy refactor before the next product step would add risk without changing documentary behavior.

## Future Refactor Conditions

- output contract remains stable;
- schema alignment tests pass on real outputs;
- module boundaries are specified before moving code;
- downstream modules are tested after every extraction change.

## Instructions for future coding agents

- run_pdf_extraction.py is the active engine.
- Do not assume `parsing/` or `evidence/` are used by the production pipeline.
- Update schema tests if output schemas evolve.
- Do not introduce ESG semantic interpretation in `ESGInformationExtraction`.
- Do not use `metric_catalog_v0.yaml` in the documentary engine.
