"""
Page 9 — PDF & Pipeline Explorer
Visualiser un PDF plein écran, puis inspecter ou lancer le pipeline par étape.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from ESGProductionControlCenter.src.esg_production_control_center.ui_components import setup_sidebar
from ESGProductionControlCenter.src.esg_production_control_center.corpus_browser import (
    get_corpus_root, browse_corpus, find_doc_workspace,
    render_pdf_page, get_pdf_page_count,
    load_json_file, load_jsonl_head, list_crops, get_stage_status,
)
from ESGProductionControlCenter.src.esg_production_control_center.pipeline_runner import (
    get_canonical_id_for_pdf, get_stage_dirs, stage_already_done,
    run_stage, STAGE_LABELS, STAGE_DESCRIPTIONS, STAGE_ORDER,
)

st.set_page_config(page_title="PDF & Pipeline Explorer", layout="wide", page_icon="🔭")
run_root = setup_sidebar("PDF & Pipeline Explorer")

st.title("🔭 PDF & Pipeline Explorer")

# ════════════════════════════════════════════════════════════
# 1 — SÉLECTION DU DOCUMENT
# ════════════════════════════════════════════════════════════
corpus_root = get_corpus_root(_ROOT)
corpus_tree = browse_corpus(corpus_root)

if not corpus_tree:
    st.error(f"❌ Corpus ESG introuvable : `{corpus_root}`")
    st.stop()

sel1, sel2, sel3 = st.columns(3)
companies = sorted(corpus_tree.keys())
company  = sel1.selectbox("🏢 Entreprise", companies, key="pdf_company")
years    = sorted(corpus_tree.get(company, {}).keys(), reverse=True)
year     = sel2.selectbox("📅 Année", years, key="pdf_year")
doc_types = sorted(corpus_tree.get(company, {}).get(year, {}).keys())
doc_type = sel3.selectbox("📄 Type de document", doc_types, key="pdf_doc_type")

pdf_path = corpus_tree.get(company, {}).get(year, {}).get(doc_type)
if pdf_path is None or not pdf_path.exists():
    st.error("❌ PDF introuvable.")
    st.stop()

page_count = get_pdf_page_count(pdf_path)

# Statut dans le run
doc_workspace = find_doc_workspace(run_root, company, year, doc_type)
is_processed  = doc_workspace is not None

if is_processed:
    stage_status = get_stage_status(doc_workspace)
    n_done = sum(stage_status.values())
    st.success(
        f"✅ Traité dans **{run_root.name}** — "
        f"{n_done}/5 étapes présentes · `{doc_workspace.name}`"
    )
else:
    canonical_id_preview = get_canonical_id_for_pdf(pdf_path)
    st.warning(
        f"⚠️ Non traité dans **{run_root.name}** · "
        f"ID futur : `{canonical_id_preview}`"
    )

st.divider()

# ════════════════════════════════════════════════════════════
# 2 — VISIONNEUSE PDF (plein écran)
# ════════════════════════════════════════════════════════════
st.markdown("### 📖 Visionneuse PDF")

if page_count == 0:
    st.error("Impossible de lire ce PDF.")
    st.stop()

# Initialiser la page courante
if "pdf_page_num" not in st.session_state:
    st.session_state["pdf_page_num"] = 1

cur = int(st.session_state["pdf_page_num"])

# Barre de navigation + qualité
nav_left, nav_slider, nav_right, nav_info, nav_qual = st.columns([1, 7, 1, 2, 3])

if nav_left.button("◀", use_container_width=True, key="btn_prev"):
    st.session_state["pdf_page_num"] = max(1, cur - 1)
    st.rerun()

page_num = nav_slider.slider(
    "Page", 1, page_count, cur,
    label_visibility="collapsed", key="pdf_slider",
)
if page_num != cur:
    st.session_state["pdf_page_num"] = page_num
    cur = page_num

if nav_right.button("▶", use_container_width=True, key="btn_next"):
    st.session_state["pdf_page_num"] = min(page_count, cur + 1)
    st.rerun()

nav_info.markdown(
    f"<div style='text-align:center;padding-top:8px;'>"
    f"<b>Page {cur}</b> / {page_count}</div>",
    unsafe_allow_html=True,
)

_DPI_OPTIONS = {"Rapide (150 DPI)": 150, "Standard (220 DPI)": 220, "Haute qualité (300 DPI)": 300}
_dpi_label = nav_qual.selectbox(
    "Qualité", list(_DPI_OPTIONS.keys()), index=1,
    label_visibility="collapsed", key="pdf_dpi",
)
_dpi = _DPI_OPTIONS[_dpi_label]

# Cache le rendu par page et par qualité
@st.cache_data(ttl=600, show_spinner=False)
def _render(pdf_str: str, page: int, dpi: int) -> bytes | None:
    return render_pdf_page(Path(pdf_str), page - 1, dpi=dpi)

with st.spinner("Rendu..."):
    img = _render(str(pdf_path), cur, _dpi)

if img:
    st.image(img, use_container_width=True)
else:
    st.error("Impossible de rendre cette page.")

st.divider()

# ════════════════════════════════════════════════════════════
# 3 — PIPELINE
# ════════════════════════════════════════════════════════════
if is_processed:

    # ── CAS A : Document traité → Inspection des sorties ────
    st.markdown("### ⚙️ Sorties du pipeline")

    tab2, tab3, tab4 = st.tabs([
        "📊 Candidats CSV",
        "🖼️ Extraction Visuelle",
        "✅ Espace de revue",
    ])

    # ── CANDIDATS CSV ───────────────────────────────────────
    with tab2:
        if not stage_status.get("02_orchestrator_csv"):
            st.info("Étape 2 (CSV) absente dans ce workspace.")
        else:
            csv_dir = doc_workspace / "02_orchestrator" / "csv"
            summ = load_json_file(csv_dir / "extraction_summary.json")
            if summ:
                s1, s2, s3 = st.columns(3)
                s1.metric("Candidats totaux",    summ.get("candidates_total", "?"))
                s2.metric("Métriques observées", summ.get("observed_metrics_count", "?"))
                s3.metric("Statut",              summ.get("status", "?"))

            CSV_FILES = [
                ("esg_information_candidates.csv", "Tous les candidats ESG", True),
                ("observed_metrics.csv",           "Métriques observées",    False),
                ("targets.csv",                    "Objectifs & cibles",     False),
                ("policies.csv",                   "Politiques",             False),
                ("risks.csv",                      "Risques",                False),
                ("visual_evidences.csv",           "Évidences visuelles",    False),
            ]
            KEY_COLS = {
                "esg_information_candidates.csv": [
                    "information_type", "esg_category", "label",
                    "raw_value", "raw_unit", "page_number", "confidence",
                ],
                "observed_metrics.csv": [
                    "label", "raw_value", "raw_unit",
                    "normalized_value", "normalized_unit", "page_number",
                ],
            }
            for fname, label, expanded in CSV_FILES:
                p = csv_dir / fname
                if not p.exists():
                    continue
                with st.expander(f"📄 {label}", expanded=expanded):
                    try:
                        df = pd.read_csv(p, dtype=str, keep_default_na=False)
                        st.caption(f"{len(df):,} lignes")
                        priority = KEY_COLS.get(fname, [])
                        show = [c for c in priority if c in df.columns] or list(df.columns[:8])
                        st.dataframe(df[show].head(500),
                                     height=320, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(str(e))

    # ── EXTRACTION VISUELLE ─────────────────────────────────
    with tab3:
        if not stage_status.get("02_orchestrator_visual"):
            st.info("Étape 3 (Visuel) absente.")
        else:
            crops = list_crops(doc_workspace)
            inv = load_json_file(
                doc_workspace / "02_orchestrator" / "visual" / "visual_input_inventory.json"
            )
            if inv:
                v1, v2, v3 = st.columns(3)
                v1.metric("Figures analysées", inv.get("figures_count", len(crops)))
                v2.metric("Crops produits",    len(crops))
                v3.metric("Statut",            inv.get("status", "ok"))

            if not crops:
                st.info("Aucun crop produit pour ce document.")
            else:
                st.markdown(f"**{len(crops)} crops visuels**")
                per_page = 9
                max_p = max(1, (len(crops) - 1) // per_page + 1)
                gp = st.number_input(
                    f"Page galerie (1–{max_p})", 1, max_p, 1, key="gallery_p"
                )
                start = (gp - 1) * per_page
                page_crops = crops[start : start + per_page]
                cols = st.columns(3)
                for i, c in enumerate(page_crops):
                    try:
                        cols[i % 3].image(
                            c.read_bytes(), caption=c.name, use_container_width=True
                        )
                    except Exception:
                        cols[i % 3].caption(f"❌ {c.name}")

    # ── ESPACE DE REVUE ─────────────────────────────────────
    with tab4:
        if not stage_status.get("04_review_workspace"):
            st.info("Étape 4 (Revue) absente.")
        else:
            ws_dir = doc_workspace / "04_review_workspace"
            rev_sum = (
                load_json_file(ws_dir / "manual_review_summary.json")
                or load_json_file(ws_dir / "review_workspace_summary.json")
            )
            if rev_sum:
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Candidats",     rev_sum.get("candidates_loaded", "?"))
                r2.metric("🟢 Utiles",     rev_sum.get("possible_indicator_count", "?"))
                r3.metric("🟡 À vérifier", rev_sum.get("needs_review_count", "?"))
                r4.metric("🔴 Bruit",      rev_sum.get("reject_candidate_count", "?"))

            ws_csv = ws_dir / "manual_review_workspace.csv"
            if ws_csv.exists():
                ws_df = pd.read_csv(ws_csv, dtype=str, keep_default_na=False)
                statuses = ["Tous"]
                if "validation_status" in ws_df.columns:
                    statuses += sorted(ws_df["validation_status"].dropna().unique())
                sf = st.selectbox("Filtrer par statut", statuses, key="ws_sf")
                if sf != "Tous" and "validation_status" in ws_df.columns:
                    ws_df = ws_df[ws_df["validation_status"] == sf]

                COLS = [c for c in [
                    "review_item_id", "validation_status", "indicator_family",
                    "label", "raw_value", "raw_unit",
                    "normalized_value", "normalized_unit",
                    "page_number", "quote", "confidence",
                ] if c in ws_df.columns]
                RENAME = {
                    "review_item_id": "ID", "validation_status": "Statut",
                    "indicator_family": "Famille", "label": "Indicateur",
                    "raw_value": "Valeur", "raw_unit": "Unité",
                    "normalized_value": "Val. norm.", "normalized_unit": "Unit. norm.",
                    "page_number": "Page", "quote": "Citation", "confidence": "Conf.",
                }
                st.caption(f"{len(ws_df):,} candidats affichés.")
                st.dataframe(
                    ws_df[COLS].rename(columns=RENAME),
                    height=480, use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "⬇️ Télécharger CSV",
                    ws_df[COLS].to_csv(index=False).encode("utf-8"),
                    f"workspace_{company}_{year}_{doc_type}.csv",
                    "text/csv",
                )

else:
    # ── CAS B : Document non traité → Lancer le pipeline ────
    st.markdown("### 🚀 Lancer le pipeline")

    with st.container(border=True):
        st.markdown(
            f"**Ce document n'a pas encore été traité dans `{run_root.name}`.**"
        )
        size_mb = pdf_path.stat().st_size // (1024 * 1024)
        t_est = max(2, page_count // 20)
        st.info(
            f"📄 {page_count} pages · 💾 {size_mb} MB · "
            f"⏱️ Durée estimée : ~{t_est}–{t_est * 2} minutes"
        )

    # Calcul de l'ID canonique et chemins de sortie
    canonical_id = get_canonical_id_for_pdf(pdf_path)
    stage_dirs   = get_stage_dirs(run_root, company, year, doc_type, canonical_id)
    done_stages  = {s: stage_already_done(stage_dirs[s], s) for s in STAGE_ORDER}

    # Afficher les étapes déjà faites si reprise partielle
    if any(done_stages.values()):
        st.markdown("##### ♻️ Étapes déjà disponibles (non relancées par défaut)")
        for s, done in done_stages.items():
            if done:
                st.caption(f"✅ {STAGE_LABELS[s]}")
        st.divider()

    # Checkboxes
    st.markdown("##### ⚙️ Étapes à exécuter")
    selected_stages = []
    for s in STAGE_ORDER:
        already = done_stages.get(s, False)
        lbl = STAGE_LABELS[s]
        if already:
            lbl += " *(déjà fait — cocher pour relancer)*"
        if st.checkbox(lbl, value=not already, key=f"chk_{s}",
                       help=STAGE_DESCRIPTIONS[s]):
            selected_stages.append(s)

    st.divider()

    if not selected_stages:
        st.info("Sélectionnez au moins une étape.")
    else:
        if st.button(
            f"🚀 Lancer {len(selected_stages)} étape(s)",
            type="primary", use_container_width=True,
        ):
            st.markdown("---")
            st.markdown("#### ⚙️ Exécution en cours...")

            placeholders = {s: st.empty() for s in selected_stages}
            for s in selected_stages:
                placeholders[s].markdown(f"⏳ **{STAGE_LABELS[s]}** — en attente...")

            pipeline_ok = True
            for stage in selected_stages:
                placeholders[stage].markdown(
                    f"🔄 **{STAGE_LABELS[stage]}** — en cours..."
                )
                result = run_stage(
                    stage=stage,
                    stage_dirs=stage_dirs,
                    pdf_path=pdf_path,
                    canonical_id=canonical_id,
                    company=company,
                    year=year,
                    doc_type=doc_type,
                    project_root=_ROOT,
                )
                if result.get("status") == "success":
                    count_key = next(
                        (k for k in result if "count" in k.lower()
                         and isinstance(result[k], int)), None,
                    )
                    extra = f" — {result[count_key]:,} éléments" if count_key else ""
                    placeholders[stage].success(
                        f"✅ **{STAGE_LABELS[stage]}** terminée{extra}"
                    )
                else:
                    err = result.get(
                        "error",
                        result.get("errors", result.get("stderr", "Erreur inconnue")),
                    )
                    if isinstance(err, list):
                        err = "; ".join(str(e) for e in err)
                    placeholders[stage].error(
                        f"❌ **{STAGE_LABELS[stage]}** — {str(err)[:200]}"
                    )
                    with st.expander("Détails", expanded=True):
                        st.json(result)
                    pipeline_ok = False
                    break

            st.divider()
            if pipeline_ok:
                st.balloons()
                st.success(
                    f"✅ Pipeline terminé ! Sorties dans "
                    f"`{run_root.name}/{company}/{year}/{doc_type}/{canonical_id}/`"
                )
                if st.button("🔄 Voir les résultats", type="primary"):
                    st.rerun()
            else:
                st.error("❌ Échec — voir l'erreur ci-dessus.")
