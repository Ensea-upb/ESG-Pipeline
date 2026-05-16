from __future__ import annotations

import os
import subprocess
from pathlib import Path


POSTPROCESSING_SCRIPTS = [
    ("build_registry", "build_registry.py"),
    ("run_deduplication", "run_deduplication.py"),
    ("build_canonical_registry", "build_canonical_registry.py"),
    ("organize_corpus", "organize_corpus.py"),
    ("organize_corpus_taxonomy", "organize_corpus_taxonomy.py"),
    ("run_validation", "run_validation.py"),
    ("select_final_documents", "select_final_documents.py"),
    ("audit_selected_documents", "audit_selected_documents.py"),
]


class PostProcessingRunner:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.postprocessing_root = self.workspace_root / "DocumentPostProcessing"

    def run_all(
        self,
        dry_run: bool = False,
        enabled_steps: dict | None = None,
        scope: str = "global",
        company_slugs: list[str] | None = None,
        years: list[int] | None = None,
        run_dir: str | Path | None = None,
        output_mode: str = "global",
    ) -> list[dict]:
        results = []
        enabled_steps = enabled_steps or {}
        company_slugs = company_slugs or []
        years = years or []
        scope = (scope or "global").lower()
        output_mode = (output_mode or "global").lower()
        run_dir_path = Path(run_dir).resolve() if run_dir else None

        output_paths: dict[str, str] = {}
        if output_mode == "run_isolated" and run_dir_path is not None:
            output_paths = {
                "input_root": str(self.workspace_root / "data" / "dossier_ingestion_0"),
                "postprocessing_root": str(run_dir_path / "postprocessing"),
                "esg_corpus_root": str(run_dir_path / "ESGCorpus"),
                "esg_corpus_taxonomy_root": str(run_dir_path / "ESGCorpusTaxonomy"),
                "esg_final_corpus_root": str(run_dir_path / "ESGFinalCorpus"),
            }
            for path_value in output_paths.values():
                Path(path_value).mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["ESG_POSTPROCESS_SCOPE"] = scope
        if scope != "global":
            env["ESG_POSTPROCESS_COMPANY_SLUGS"] = ",".join(company_slugs)
            env["ESG_POSTPROCESS_YEARS"] = ",".join(str(year) for year in years)
        if output_paths:
            env["ESG_POSTPROCESS_INPUT_ROOT"] = output_paths["input_root"]
            env["ESG_POSTPROCESS_OUTPUT_ROOT"] = output_paths["postprocessing_root"]
            env["ESG_POSTPROCESS_ESG_CORPUS_ROOT"] = output_paths["esg_corpus_root"]
            env["ESG_POSTPROCESS_ESG_CORPUS_TAXONOMY_ROOT"] = output_paths[
                "esg_corpus_taxonomy_root"
            ]
            env["ESG_POSTPROCESS_ESG_FINAL_CORPUS_ROOT"] = output_paths[
                "esg_final_corpus_root"
            ]

        for step_name, script_name in POSTPROCESSING_SCRIPTS:
            if enabled_steps.get(step_name, True) is False:
                results.append({"script": script_name, "status": "disabled"})
                continue
            script_path = self.postprocessing_root / "scripts" / script_name
            command = ["python", str(script_path)]
            if script_name == "audit_selected_documents.py":
                command.append("--overwrite")
            if dry_run:
                results.append(
                    {
                        "script": script_name,
                        "status": "dry_run",
                        "command": command,
                        "scope": scope,
                        "output_mode": output_mode,
                        "output_paths": output_paths,
                        "company_slugs": company_slugs,
                        "years": years,
                    }
                )
                continue
            if not script_path.exists():
                results.append({"script": script_name, "status": "skipped_missing"})
                continue
            completed = subprocess.run(
                command,
                cwd=self.postprocessing_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=3600,
            )
            results.append(
                {
                    "script": script_name,
                    "status": "success" if completed.returncode == 0 else "failed",
                    "returncode": completed.returncode,
                    "stdout_tail": completed.stdout[-1000:],
                    "stderr_tail": completed.stderr[-1000:],
                    "scope": scope,
                    "output_mode": output_mode,
                    "output_paths": output_paths,
                }
            )
        return results
