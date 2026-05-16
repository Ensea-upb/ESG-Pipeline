# ESG Orchestrator

Offline-first orchestration layer for the ESG document corpus pipeline.

The orchestrator reads companies, document types, years and run profiles from
YAML configuration files. It can build the task matrix, run retriever scripts,
resume run state, execute DocumentPostProcessing steps, and produce run-level
coverage reports.

## Safety

Do not run the full CAC 40 x 5 years profile casually. Start with dry-run:

```powershell
python scripts\run_pipeline.py --profile pilot --dry-run
```

The dry-run creates:

- `runs/<run_id>/run_state.json`
- `runs/<run_id>/task_log.csv`
- `runs/<run_id>/coverage_matrix.csv`
- `runs/<run_id>/final_summary.json`

## Real Pilot

After reviewing the dry-run task matrix:

```powershell
python scripts\run_pipeline.py --profile pilot
```

## Profiles

Profiles live in `config/run_profiles.yaml`.
