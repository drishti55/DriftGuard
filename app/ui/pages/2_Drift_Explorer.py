import streamlit as st
import time
import pandas as pd
from pathlib import Path
from app.analysis.llm_client import LLMClient
from app.analysis.drift_pipeline import DriftPipeline
from app.validation.fix_validator import validate_fix

st.title("🔍 Drift Explorer")

if not st.session_state.get("repo_info"):
    st.warning("Please load a repository in the Overview page first.")
    st.stop()

info = st.session_state.repo_info
repo = st.session_state.ingested_repo

# Validate the RepoInfo object has all expected fields (guards against stale session state).
_required = ['scan_metrics', 'drift_candidates', 'artifacts', 'artifact_type_counts']
_stale = any(not hasattr(info, f) for f in _required) or not getattr(info, 'scan_metrics', None) or 'files_discovered' not in info.scan_metrics
if _stale:
    st.warning(
        "The loaded repository analysis is outdated. "
        "Please return to the Overview page and click **Rescan Repository** to refresh."
    )
    st.stop()

metrics = getattr(info, 'scan_metrics', {}) or {}

st.markdown(f"**Repository:** `{repo.original_source}` &nbsp;|&nbsp; **Language:** `{info.language}` &nbsp;|&nbsp; **Commit:** `{info.commit_sha[:8] if info.commit_sha else 'N/A'}`")

# All counts come from scan_metrics populated by RepositoryScanner.scan().
# Missing keys show "—" so we never silently convert absent data to zero.
def _mv(key):
    return metrics.get(key)

c1, c2, c3, c4 = st.columns(4)
with c1:
    v = _mv("files_discovered")
    st.metric("Discovered Files", v if v is not None else "—")
with c2:
    v = _mv("relevant_artifacts")
    st.metric("Relevant Artifacts", v if v is not None else "—")
with c3:
    vc = _mv("ignored_vendor_cache")
    vb = _mv("ignored_binary")
    ignored = (vc or 0) + (vb or 0) if (vc is not None or vb is not None) else None
    st.metric("Ignored (Vendor/Binaries)", ignored if ignored is not None else "—")
with c4:
    v = _mv("candidates_generated")
    st.metric("Drift Candidates", v if v is not None else "—")

st.markdown("---")

def run_pipeline_analysis(model: str, max_candidates: int = None):
    """Run analysis over relationship candidates using DriftPipeline."""
    llm = LLMClient(model=model)
    pipeline = DriftPipeline(workspace_path=repo.workspace_path, llm_client=llm)

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, msg):
        progress_bar.progress(min(current / total, 1.0))
        status_text.markdown(f"**Status:** {msg}")

    result = pipeline.analyze_repository(
        repo_info=info,
        max_candidates=max_candidates,
        progress_callback=update_progress
    )

    st.session_state.pipeline_result = result
    st.session_state.reports = result["reports"]
    st.session_state.analysis_running = False
    status_text.success("Analysis complete!")
    st.rerun()

def render_analysis_configuration():
    st.header("Analysis Configuration")
    c1, c2 = st.columns(2)
    with c1:
        model = st.selectbox("Reasoning Model", ["qwen2.5-coder:7b", "codellama:7b", "starcoder2:3b", "gemma2:9b"])
    with c2:
        # candidate count from scan_metrics; fallback to drift_candidates list length
        sm = getattr(info, 'scan_metrics', {}) or {}
        candidate_count = sm.get('candidates_generated',
                                 len(getattr(info, 'drift_candidates', [])))
        coverage_mode = st.radio(
            "Candidate Coverage",
            [f"Analyze All Candidates ({candidate_count})", "Run Initial Batch (First 50 Candidates)"],
            index=0
        )
        max_candidates = None if "Analyze All" in coverage_mode else 50

    if st.button("🚀 Run Drift Analysis", type="primary", disabled=st.session_state.get("analysis_running", False)):
        st.session_state.analysis_running = True
        run_pipeline_analysis(model, max_candidates)

def render_drift_dashboard():
    result = st.session_state.get("pipeline_result")
    reports = st.session_state.get("reports", [])
    if not reports or not result:
        return

    st.markdown("---")
    st.header("DRIFT ANALYSIS")

    res_metrics = result.get("metrics", {})
    status = result.get("status", "NO DRIFT FOUND")
    confirmed_drifts = result.get("confirmed_drifts", [])
    analyzed_count = res_metrics.get("candidates_analyzed", len(reports))
    total_candidates = res_metrics.get("candidates_generated", len(reports))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Candidates Generated", total_candidates)
    with col2:
        st.metric("Candidates Analyzed", analyzed_count)
    with col3:
        st.metric("Candidates Verified", res_metrics.get("candidates_verified", analyzed_count))
    with col4:
        st.metric("Confirmed Drifts", len(confirmed_drifts))

    st.markdown("---")

    if status == "DRIFT DETECTED" or len(confirmed_drifts) > 0:
        st.error(f"## 🚨 {len(confirmed_drifts)} CONFIRMED DRIFT{'S' if len(confirmed_drifts) != 1 else ''} FOUND")

        for idx, r in enumerate(confirmed_drifts):
            pred = r.prediction
            type_label = pred.drift_type.replace('_', ' ').title() if pred else "Cross Artifact"
            lines_1 = getattr(pred, 'file_1_lines', None) or getattr(pred, 'artifact_1_lines', None) or "N/A"
            lines_2 = getattr(pred, 'file_2_lines', None) or getattr(pred, 'artifact_2_lines', None) or "N/A"

            with st.container():
                st.markdown(f"### DRIFT {idx + 1:02d} — {type_label}")
                st.markdown(f"`{r.artifact_1_path}` (Lines {lines_1}) &nbsp;↔&nbsp; `{r.artifact_2_path}` (Lines {lines_2})")

                ev1 = getattr(r, 'real_evidence_1', '') or getattr(pred, 'extracted_fact_1', '') or "[Not extracted]"
                ev2 = getattr(r, 'real_evidence_2', '') or getattr(pred, 'extracted_fact_2', '') or "[Not extracted]"

                with st.expander("📄 View Confirmed Evidence from Repository", expanded=True):
                    st.markdown(f"**{r.artifact_1_path}** (Lines {lines_1}):")
                    st.code(ev1)
                    st.markdown(f"**{r.artifact_2_path}** (Lines {lines_2}):")
                    st.code(ev2)

                contradiction = getattr(pred, 'contradiction_rationale', '') or getattr(pred, 'evidence', '')
                st.markdown(f"**Contradiction:** {contradiction}")
                st.markdown("---")

    elif status == "ANALYSIS INCOMPLETE":
        remaining = res_metrics.get("candidates_remaining", total_candidates - analyzed_count)
        st.warning(f"## ⚠️ ANALYSIS INCOMPLETE")
        st.markdown(f"**Candidates Analyzed:** `{analyzed_count}` &nbsp;|&nbsp; **Candidates Remaining:** `{remaining}`")
        st.info("DriftGuard does not infer 'No Drift' from a partial repository scan. All candidates must be analyzed.")

    else:
        st.success("## ✅ NO DRIFT FOUND")
        st.markdown(f"The analyzed repository is **consistent across all {analyzed_count} checked relationship candidates**.")
        checked_types = sorted({r.artifact_1_type for r in reports} | {r.artifact_2_type for r in reports})
        if checked_types:
            st.info("Checked Artifact Categories:\n" + "\n".join(f"- {t.replace('_', ' ').title()}" for t in checked_types))

def render_file_analysis_view():
    """File Analysis Inventory View"""
    st.markdown("---")
    st.header("Repository File Inventory")
    artifacts = info.artifacts

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Status Filter", ["All Discovered Files", "RELEVANT Files Only", "IGNORED Files Only"], key="exp_status_filter")
    with col2:
        cats = sorted(list({getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')) for a in artifacts}))
        cat_filter = st.selectbox("Category Filter", ["All Categories"] + cats, key="exp_cat_filter")

    filtered = artifacts
    if status_filter == "RELEVANT Files Only":
        filtered = [a for a in filtered if a.status == "RELEVANT"]
    elif status_filter == "IGNORED Files Only":
        filtered = [a for a in filtered if a.status == "IGNORED"]

    if cat_filter != "All Categories":
        filtered = [a for a in filtered if getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')) == cat_filter]

    data = []
    for a in filtered[:200]:
        data.append({
            "Path": a.path,
            "Category": getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')),
            "Type": getattr(a, 'file_type', getattr(a, 'artifact_type', 'other')),
            "Language": getattr(a, 'language', '') or "-",
            "Lines": getattr(a, 'line_count', '-') if getattr(a, 'status', 'RELEVANT') == "RELEVANT" else "-",
            "Size (KB)": round(getattr(a, 'file_size', getattr(a, 'size_bytes', 0)) / 1024, 1),
            "Status": getattr(a, 'status', 'RELEVANT'),
            "Relationships": getattr(a, 'relationships_count', 0),
            "Ignore Reason": getattr(a, 'ignore_reason', None) or "-",
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True)

# Render main page flow
render_analysis_configuration()
render_drift_dashboard()
render_file_analysis_view()
