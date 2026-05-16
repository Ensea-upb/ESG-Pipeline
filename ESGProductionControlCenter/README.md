# ESGProductionControlCenter

Local Streamlit control center for the ESG production pipeline.

It orchestrates existing modules only:

- ESGCSVExtraction
- ESGVisualExtraction
- ESGTableExtraction
- ESGExtractionOrchestrator
- ESGIndicatorValidation
- ESGManualReview
- ESGIndicatorDatabase

It does not create ESG scores, ESG ratings, or final validated indicators.
`accepted_candidate` is not presented as `validated_indicator`, and
`indicator_database_status=preparation_only` remains visible.

Run the interface:

```powershell
streamlit run ESGProductionControlCenter/app.py
```

## v1.1 - Business UI

The main page is now `Poste de controle`.

The UI is organized around a business workflow:

1. choose a company;
2. choose a year;
3. choose a document;
4. launch a simulation or confirmed run;
5. follow progress;
6. inspect business-readable results;
7. perform human review;
8. inspect and download preparation-only outputs.

Technical module names, paths, and IDs remain available in technical detail
sections, but they no longer dominate the main workflow.

See:

- `docs/USER_GUIDE_BUSINESS_UI_V1_1.md`
- `docs/RELEASE_NOTES_V1_1.md`
- `docs/VALIDATION_COMMANDS_V1_1.md`

## v1.2 - Demo / sandbox mode

v1.2 adds a synthetic demo workspace so the full UI can be tested without real
Onyxia outputs.

Create the demo:

```powershell
python ESGProductionControlCenter/scripts/create_demo_workspace.py --overwrite
```

Then run the app and open `Parcours guidé démo`:

```powershell
streamlit run ESGProductionControlCenter/app.py
```

Demo data is synthetic only. It is marked with `demo_data=true` and
`synthetic_source=true`. It produces no ESG score and no final validated
indicator.

See:

- `docs/DEMO_MODE_GUIDE_V1_2.md`
- `docs/RELEASE_NOTES_V1_2.md`
- `docs/VALIDATION_COMMANDS_V1_2.md`

Main operator pages:

- `Pipeline complet`: select an ESGInformationExtraction output, inspect the full chain, view each command, run dry-runs, execute a confirmed step, and validate contracts step by step.
- `Outputs disponibles`: discover all known outputs across the production chain.
- `Plan de commandes`: generate a command without executing it.
- `Validations contrats`: run module contract validators and display errors/warnings.
- `Logs`: inspect run state, stdout, and stderr.
- `CSV Explorer`: browse and filter generated CSV files in read-only mode.
- `Manual Review`: load a review workspace and export explicit human decisions.
- `Indicator Database`: inspect the preparation-only database and keep `indicator_database_status=preparation_only` visible.

Backend dry-run:

```powershell
python ESGProductionControlCenter/scripts/run_control_center.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGProductionControlCenter/outputs/lvmh_control_center_v10_test" `
  --dry-run `
  --overwrite
```
