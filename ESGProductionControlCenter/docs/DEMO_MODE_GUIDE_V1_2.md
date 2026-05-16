# Demo Mode Guide v1.2

## Purpose

Demo mode lets users test the business workflow without waiting for real Onyxia
outputs.

All demo files are synthetic and clearly marked with:

- `demo_data=true`
- `synthetic_source=true`

## Create Demo Workspace

```powershell
python ESGProductionControlCenter/scripts/create_demo_workspace.py --overwrite
```

Output:

`ESGProductionControlCenter/outputs/demo/demo_company_2024/`

## Use in Streamlit

1. Run `streamlit run ESGProductionControlCenter/app.py`.
2. Open `Parcours guidé démo`, or use `Poste de controle`.
3. Toggle `Utiliser un exemple de démonstration`.
4. Select `Demo Luxury Group / 2024`.

## Safety

Demo data is not real ESG data. It produces no ESG score and no final validated
indicator. The preparation database remains `preparation_only`.
