from __future__ import annotations

from pathlib import Path

from ESGOrchestrator.src.esg_orchestrator.postprocessing_runner import PostProcessingRunner


def test_postprocessing_runner_includes_quality_audit_in_dry_run(tmp_path):
    runner = PostProcessingRunner(workspace_root=Path.cwd())

    results = runner.run_all(
        dry_run=True,
        enabled_steps={},
        scope="run",
        company_slugs=["lvmh"],
        years=[2024],
        run_dir=tmp_path / "run",
        output_mode="run_isolated",
    )

    audit = next(item for item in results if item["script"] == "audit_selected_documents.py")
    assert audit["status"] == "dry_run"
    assert audit["command"][-1] == "--overwrite"
    assert audit["output_paths"]["postprocessing_root"].endswith("postprocessing")
