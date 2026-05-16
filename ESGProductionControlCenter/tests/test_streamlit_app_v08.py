import importlib


def test_app_import_has_no_side_effects():
    app = importlib.import_module("ESGProductionControlCenter.app")
    assert hasattr(app, "render_app")
    assert "Aucun indicateur ESG final validé" in app.SAFETY_TEXT
