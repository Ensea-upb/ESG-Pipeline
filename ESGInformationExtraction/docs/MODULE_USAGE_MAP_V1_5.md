# Module Usage Map v1.5

`run_pdf_extraction.py` is the current source of truth for the production PDF documentary engine.

| Path | Classification | Used by run_pdf_extraction.py | Used by tools | Used by tests | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `run_pdf_extraction.py` | active_engine_core | yes | indirect | yes | keep |
| `tools/` | active_tooling | no | yes | yes | keep |
| `schemas/` | schema_support | no | indirect | yes | keep and align with real outputs |
| `contracts/output_contract_v1.json` | schema_support | no | yes | yes | keep stable |
| `config/extraction_config.yaml` | config_support | limited/none | no | no | document current role |
| `config/section_taxonomy_v0.yaml` | config_support | partial/duplicated | no | no | future refactor to single source |
| `config/metric_catalog_v0.yaml` | reserved_for_future | no | no | no | reserve for downstream ESG layers |
| `parsing/` | legacy_or_experimental | no | no | limited/unknown | document as legacy until refactor |
| `section_detection/` | legacy_or_experimental | no | no | limited/unknown | document as legacy until refactor |
| `extraction/` | reserved_for_future | no | no | limited/unknown | do not treat as active engine |
| `evidence/` | legacy_or_experimental | no | no | limited/unknown | document as legacy until refactor |
| `quality_control/` | legacy_or_experimental | no | no | limited/unknown | document as legacy until refactor |
| `document_base/` | reserved_for_future | no | no | limited/unknown | keep separate from active PDF engine |

Future agents should not assume that package directories are used by the production pipeline. The active behavior is in `run_pdf_extraction.py`.
