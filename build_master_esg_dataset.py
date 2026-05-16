"""
build_master_esg_dataset.py — Terminus du pipeline ESG.

Scanne tous les runs dans EXTERNAL_AUDIT_RUNS/, agrège les indicateurs
validés et produit deux fichiers dans MASTER_ESG_OUTPUT/ :

  esg_values.csv   — tableau wide  : une ligne par (company, year),
                     une colonne par variable ESG (31 variables).
  esg_lineage.csv  — traçabilité   : une ligne par valeur retenue,
                     avec source PDF, page, citation, reviewer.

Peut être relancé à tout moment ; reflète l'état courant du pipeline.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ── Configuration ─────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
_AUDIT_ROOT   = _PROJECT_ROOT / "EXTERNAL_AUDIT_RUNS"
_OUTPUT_DIR   = _PROJECT_ROOT / "MASTER_ESG_OUTPUT"
_INDEX_PATH   = _PROJECT_ROOT / "DocumentPostProcessing/data/quality_audit_v2/extraction_index_strict_likely_valid.csv"
_CONTRACT     = _PROJECT_ROOT / "ESGVariableDatasetBuilder/contracts/esg_variables_dataset_contract_v0.json"

# 31 variables ESG officielles
ESG_VARIABLES: list[str] = [
    "co2_emissions", "carbon_intensity", "energy_consumption", "water_consumption",
    "waste", "biodiversity", "fossil_exposure", "turnover", "diversity",
    "work_accidents", "human_capital", "supply_chain", "human_rights",
    "board_independence", "ceo_chairman_separation", "remuneration",
    "shareholder_rights", "transparency", "esg_scandals", "fraud", "corruption",
    "pollution", "lawsuits", "social_controversies", "market_cap", "volatility",
    "leverage", "roa", "roe", "liquidity", "stock_returns",
]

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_variable_list() -> list[str]:
    """Charge la liste officielle depuis le contrat si disponible."""
    if _CONTRACT.exists():
        try:
            data = json.loads(_CONTRACT.read_text(encoding="utf-8"))
            v = data.get("variables", [])
            if isinstance(v, list) and v:
                return [str(x) for x in v]
        except Exception:
            pass
    return ESG_VARIABLES


def _load_index() -> pd.DataFrame:
    """Charge l'index des documents avec le chemin PDF."""
    if _INDEX_PATH.exists():
        return pd.read_csv(_INDEX_PATH)
    return pd.DataFrame(columns=["company_slug", "fiscal_year", "final_path", "company_name"])


def _find_indicator_dbs() -> list[Path]:
    """Retourne tous les indicator_preparation_database.csv trouvés."""
    paths: list[Path] = []
    if not _AUDIT_ROOT.exists():
        return paths
    for p in sorted(_AUDIT_ROOT.rglob("indicator_preparation_database.csv")):
        paths.append(p)
    log.info("Trouvé %d indicator_preparation_database.csv", len(paths))
    return paths


def _parse_run_info(db_path: Path) -> dict:
    """Extrait run_id depuis le chemin (company/year lus directement dans le CSV)."""
    parts = db_path.parts
    run_id = "unknown"
    try:
        for i, part in enumerate(parts):
            if part == "EXTERNAL_AUDIT_RUNS" and i + 1 < len(parts):
                run_id = parts[i + 1]
                break
    except Exception:
        pass
    return {"run_id": run_id}


def _load_db(db_path: Path, run_info: dict, index_df: pd.DataFrame) -> pd.DataFrame:
    """Charge un indicator_preparation_database.csv et enrichit avec métadonnées."""
    try:
        df = pd.read_csv(db_path)
    except Exception as exc:
        log.warning("Impossible de lire %s : %s", db_path, exc)
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # company_slug et fiscal_year : lire depuis le CSV en priorité
    company_slug = str(df["company"].iloc[0]).strip() if "company" in df.columns else "unknown"
    fiscal_year  = str(df["fiscal_year"].iloc[0]).strip() if "fiscal_year" in df.columns else "unknown"

    # Enrichit depuis l'index CSV (company_name + source_pdf)
    idx_row = index_df[
        (index_df["company_slug"] == company_slug)
        & (index_df["fiscal_year"].astype(str) == str(fiscal_year))
    ]
    company_name = idx_row["company_name"].iloc[0] if not idx_row.empty else company_slug
    source_pdf   = idx_row["final_path"].iloc[0]   if not idx_row.empty else ""

    df["_run_id"]       = run_info["run_id"]
    df["_canonical_id"] = df.get("document_id", pd.Series("unknown", index=df.index))
    df["_company_name"] = company_name
    df["_source_pdf"]   = source_pdf

    return df


def _select_best_value(group: pd.DataFrame) -> pd.Series:
    """
    Pour un (company, year, indicator_key) dupliqué entre plusieurs runs,
    choisit la meilleure ligne : is_final_indicator=True en priorité,
    puis la plus haute confiance, puis la plus récente.
    """
    if "is_final_indicator" in group.columns:
        final = group[group["is_final_indicator"].astype(str).str.lower() == "true"]
        if not final.empty:
            group = final

    if "indicator_schema_confidence" in group.columns:
        group = group.sort_values("indicator_schema_confidence", ascending=False)

    return group.iloc[0]


# ── Construction des fichiers ─────────────────────────────────────────────────

def build(output_dir: Path, overwrite: bool = False) -> dict:
    """Point d'entrée principal. Retourne un dict résumé."""
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"{output_dir} existe déjà et n'est pas vide. Utilisez --overwrite."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    variables   = _load_variable_list()
    index_df    = _load_index()
    db_paths    = _find_indicator_dbs()

    # ── 1. Collecte tous les indicateurs ─────────────────────────────────────
    frames: list[pd.DataFrame] = []
    for db_path in db_paths:
        run_info = _parse_run_info(db_path)
        df = _load_db(db_path, run_info, index_df)
        if not df.empty:
            frames.append(df)
            co = df["company"].iloc[0] if "company" in df.columns else "?"
            yr = df["fiscal_year"].iloc[0] if "fiscal_year" in df.columns else "?"
            log.info("  %s · %s [%s] → %d lignes", co, yr, run_info["run_id"], len(df))

    if not frames:
        log.warning("Aucune donnée trouvée. Les fichiers de sortie seront vides.")
        all_data = pd.DataFrame()
    else:
        all_data = pd.concat(frames, ignore_index=True)
        log.info("Total brut : %d lignes", len(all_data))

    # ── 2. Filtrage : uniquement les indicateurs finaux ───────────────────────
    if not all_data.empty and "indicator_key" in all_data.columns:
        # Garde uniquement les lignes avec une indicator_key connue
        all_data = all_data[all_data["indicator_key"].isin(variables)]

        # Garde uniquement les lignes avec une valeur préparée
        if "value_prepared" in all_data.columns:
            all_data = all_data[all_data["value_prepared"].notna() & (all_data["value_prepared"].astype(str).str.strip() != "")]

        log.info("Après filtrage variables connues + valeur non-nulle : %d lignes", len(all_data))

    # ── 3. Déduplique : meilleure valeur par (company, year, variable) ────────
    if not all_data.empty:
        key_cols = ["company", "fiscal_year", "indicator_key"]
        available_keys = [c for c in key_cols if c in all_data.columns]
        if len(available_keys) == 3:
            best_rows = (
                all_data
                .groupby(available_keys, group_keys=False)
                .apply(_select_best_value, include_groups=False)
                .reset_index(drop=True)
            )
        else:
            best_rows = all_data
        log.info("Après déduplication : %d valeurs uniques", len(best_rows))
    else:
        best_rows = pd.DataFrame()

    # ── 4. Construction esg_lineage.csv ───────────────────────────────────────
    lineage_cols = {
        "company":          "company_slug",
        "_company_name":    "company_name",
        "fiscal_year":      "fiscal_year",
        "indicator_family": "indicator_family",
        "indicator_key":    "variable",
        "indicator_label":  "variable_label",
        "value_prepared":   "value",
        "unit_prepared":    "unit",
        "year_prepared":    "reference_year",
        "value_raw":        "value_raw",
        "unit_raw":         "unit_raw",
        "page_number":      "source_page",
        "quote":            "source_quote",
        "reviewer":         "reviewer",
        "decision_reason":  "decision_reason",
        "reviewer_notes":   "reviewer_notes",
        "_source_pdf":      "source_pdf",
        "_canonical_id":    "canonical_id",
        "_run_id":          "run_id",
        "source_engine":    "source_engine",
        "indicator_schema_confidence": "schema_confidence",
    }

    if not best_rows.empty:
        present = {k: v for k, v in lineage_cols.items() if k in best_rows.columns}
        lineage_df = best_rows[list(present.keys())].rename(columns=present).copy()
    else:
        lineage_df = pd.DataFrame(columns=list(lineage_cols.values()))

    lineage_path = output_dir / "esg_lineage.csv"
    lineage_df.to_csv(lineage_path, index=False, encoding="utf-8")
    log.info("esg_lineage.csv → %d lignes", len(lineage_df))

    # ── 5. Construction esg_values.csv (format wide) ──────────────────────────
    if not best_rows.empty and "indicator_key" in best_rows.columns and "value_prepared" in best_rows.columns:
        # Colonnes d'identité
        id_cols: list[str] = []
        for c in ["_company_name", "company", "fiscal_year"]:
            if c in best_rows.columns:
                id_cols.append(c)

        pivot_df = best_rows.pivot_table(
            index=id_cols,
            columns="indicator_key",
            values="value_prepared",
            aggfunc="first",
        ).reset_index()

        # Renomme les colonnes d'identité
        rename_id = {"_company_name": "company_name", "company": "company_slug"}
        pivot_df = pivot_df.rename(columns=rename_id)
        pivot_df.columns.name = None

        # Ajoute les variables manquantes avec NaN
        for var in variables:
            if var not in pivot_df.columns:
                pivot_df[var] = pd.NA

        # Réordonne : identity cols + variables dans l'ordre officiel
        identity = [c for c in ["company_name", "company_slug", "fiscal_year"] if c in pivot_df.columns]
        values_df = pivot_df[identity + variables]
    else:
        # Tableau vide mais avec la bonne structure
        values_df = pd.DataFrame(columns=["company_name", "company_slug", "fiscal_year"] + variables)

    values_path = output_dir / "esg_values.csv"
    values_df.to_csv(values_path, index=False, encoding="utf-8")
    log.info("esg_values.csv → %d lignes, %d variables", len(values_df), len(variables))

    # ── 6. Résumé ─────────────────────────────────────────────────────────────
    found_cells   = int(values_df[variables].notna().sum().sum()) if not values_df.empty else 0
    total_cells   = len(values_df) * len(variables)
    missing_cells = total_cells - found_cells

    summary = {
        "built_at":               datetime.now(timezone.utc).isoformat(),
        "sources_scanned":        len(db_paths),
        "company_year_rows":      len(values_df),
        "variables":              len(variables),
        "lineage_rows":           len(lineage_df),
        "found_values":           found_cells,
        "missing_values":         missing_cells,
        "completion_pct":         round(found_cells / total_cells * 100, 1) if total_cells else 0.0,
        "output_dir":             str(output_dir),
        "esg_values_path":        str(values_path),
        "esg_lineage_path":       str(lineage_path),
    }
    summary_path = output_dir / "build_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info(
        "=== Build terminé — %d valeurs trouvées / %d possibles (%.1f%%)",
        found_cells, total_cells, summary["completion_pct"],
    )
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Construit esg_values.csv + esg_lineage.csv depuis tous les runs du pipeline.",
    )
    p.add_argument(
        "--output-dir", default=str(_OUTPUT_DIR),
        help=f"Répertoire de sortie (défaut : {_OUTPUT_DIR})",
    )
    p.add_argument(
        "--overwrite", action="store_true",
        help="Écrase le répertoire de sortie existant.",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    try:
        summary = build(Path(args.output_dir), overwrite=args.overwrite)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)
    except FileExistsError as e:
        log.error(str(e))
        sys.exit(1)
