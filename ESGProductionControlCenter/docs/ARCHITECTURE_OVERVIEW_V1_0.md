# ESGProductionControlCenter Architecture Overview v1.0

The module is a control plane over existing engines. It contains no ESG scoring
logic and no final indicator validation logic.

The backend modules are pure Python helpers. `app.py` renders the Streamlit UI
and only executes commands when the user clicks explicit controls.
