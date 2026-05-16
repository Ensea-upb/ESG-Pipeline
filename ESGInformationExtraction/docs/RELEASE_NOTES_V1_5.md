# ESGInformationExtraction v1.5 — Architecture Hygiene Release

This release hardens the documentary engine without changing extraction behavior or the 23 output files.

Changes:

- synchronized Pydantic schemas with real outputs;
- added architecture hygiene audit tooling;
- documented module usage and legacy/experimental directories;
- clarified config/catalog roles;
- documented reserved enum values in the output contract;
- added real-output schema alignment tests.

No ESG extraction, scoring, OCR, LLM, RAG, or metric validation is added.
