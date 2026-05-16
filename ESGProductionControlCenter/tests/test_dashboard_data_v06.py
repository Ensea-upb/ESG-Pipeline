from ESGProductionControlCenter.src.esg_production_control_center.dashboard_data import PAGES, build_dashboard_data
from ESGProductionControlCenter.src.esg_production_control_center.csv_viewer import load_csv


def test_dashboard_data_shape():
    data = build_dashboard_data(".")
    assert "Aucun indicateur ESG final validé" in data["safety_banner"]
    assert PAGES == ["Poste de contrôle", "Exploration", "Logs", "Guide"]
    assert "outputs" in data


def test_csv_viewer_handles_empty_csv(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    df = load_csv(empty)
    assert df.empty
