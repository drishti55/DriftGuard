import streamlit as st
import pandas as pd
import altair as alt
import json
from pathlib import Path
from app.experiments.runner import ExperimentRunner

st.set_page_config(page_title="Model & Pipeline Comparison", page_icon="📊", layout="wide")

st.title("📊 Model & Pipeline Comparison")
st.markdown("Auditable benchmarks, RAG vs. Non-RAG comparisons, and full case-level experiment records.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

runner = st.session_state.runner
experiments = runner.get_experiments()

if not experiments:
    st.info("No experiment results found. Go to the **Experiment Lab** to launch an experiment or run `python3 run_experiments.py --smoke-test`.")
    st.stop()

# ==========================================
# 1. FILTERS & DATA PREPARATION
# ==========================================
with st.sidebar:
    st.header("🔍 Filter Experiments")
    from app.config import SUPPORTED_MODELS
    all_models = SUPPORTED_MODELS
    all_splits = sorted(list(set(e.config.dataset_split for e in experiments)))
    all_rag = sorted(list(set(e.config.rag_mode for e in experiments)))
    
    selected_models = st.multiselect("Models", all_models, default=all_models)
    selected_splits = st.multiselect("Dataset Splits", all_splits, default=all_splits)
    selected_rag = st.multiselect("RAG Modes", all_rag, default=all_rag)
    
    st.markdown("---")
    include_smoke_tests = st.checkbox("Include Smoke / Debug Runs", value=False)

# Filter experiments
filtered_exps = [
    e for e in experiments 
    if e.config.model in selected_models 
    and e.config.dataset_split in selected_splits
    and e.config.rag_mode in selected_rag
    and (include_smoke_tests or not getattr(e.config, "debug_sample_mode", False))
]

if not filtered_exps:
    st.warning("No experiments match the current sidebar filter selections. The Experiment Plan below is still available.")

# Helper for displaying values with N/A instead of fake zeroes
def fmt_val(v, is_pct=False):
    if v is None:
        return "N/A"
    try:
        f = float(v)
        return f"{f * 100:.1f}%" if is_pct else f"{f:.4f}"
    except (ValueError, TypeError):
        return "N/A"

# ==========================================
# EXPERIMENT PLAN (always visible)
# ==========================================
st.header("📋 EXPERIMENT PLAN")
st.markdown("Complete planned matrix generated from configured models and actual dataset dimensions. This is a **plan**, not completed results.")

from app.experiments.planner import (
    generate_experiment_matrix, get_total_dataset_stats, 
    check_model_availability, reconcile_with_existing_runs, matrix_summary
)

def _load_plan():
    stats = get_total_dataset_stats()
    matrix = generate_experiment_matrix()
    matrix = reconcile_with_existing_runs(matrix, Path("results/experiments"))
    summary = matrix_summary(matrix)
    return stats, matrix, summary

def _check_models():
    return check_model_availability()

dataset_stats, plan_matrix, plan_summary = _load_plan()
model_avail = _check_models()

# Dataset & Scale Overview
plan_tab_overview, plan_tab_matrix, plan_tab_models = st.tabs([
    "Scale Overview", "Full Planned Matrix", "Model Availability"
])

with plan_tab_overview:
    sc = dataset_stats["splits"]
    
    st.markdown("#### Dataset Dimensions")
    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
    dc1.metric("Train Cases", f"{sc['Train']['cases']:,}")
    dc2.metric("Validation Cases", f"{sc['Validation']['cases']:,}")
    dc3.metric("Test Cases", f"{sc['Test']['cases']:,}")
    dc4.metric("Total Cases", f"{dataset_stats['total_cases']:,}")
    dc5.metric("Unique Repositories", f"{dataset_stats['unique_repositories']}")
    
    st.markdown("#### Experiment Scale")
    ec1, ec2, ec3, ec4, ec5 = st.columns(5)
    ec1.metric("Configured Models", len(SUPPORTED_MODELS))
    ec2.metric("Dataset Splits", 3)
    ec3.metric("RAG Modes", 2)
    ec4.metric("Base Configurations", plan_summary["total_configurations"])
    ec5.metric("Planned Case Evaluations", f"{plan_summary['planned_evaluations']:,}")
    
    st.markdown("#### Execution Progress")
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Evaluated So Far", f"{plan_summary['evaluated_so_far']:,}")
    pc2.metric("Remaining", f"{plan_summary['remaining']:,}")
    progress_pct = plan_summary["evaluated_so_far"] / plan_summary["planned_evaluations"] if plan_summary["planned_evaluations"] > 0 else 0
    pc3.metric("Progress", f"{progress_pct * 100:.2f}%")
    
    st.markdown("#### Status Breakdown")
    status_data = []
    for status, count in sorted(plan_summary["status_breakdown"].items()):
        status_data.append({"Status": status, "Configurations": count})
    st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)

with plan_tab_matrix:
    st.markdown("Each row is a planned experiment configuration. Status reflects reconciliation with existing runs.")
    plan_rows = []
    for p in plan_matrix:
        plan_rows.append({
            "Model": p.model,
            "Split": p.dataset_split,
            "RAG Mode": p.rag_mode,
            "Expected Cases": f"{p.expected_cases:,}",
            "Expected Repos": p.expected_repositories,
            "Evaluated": f"{p.evaluated_cases:,}",
            "Remaining": f"{p.remaining_cases:,}",
            "Successful": f"{p.successful_cases:,}",
            "Failed": p.failed_cases,
            "Unavailable": p.unavailable_cases,
            "Status": p.status,
            "Experiment ID": p.experiment_id or "—",
        })
    st.dataframe(pd.DataFrame(plan_rows), use_container_width=True, hide_index=True)

with plan_tab_models:
    st.markdown("Ollama availability for each configured model.")
    model_rows = []
    for m in SUPPORTED_MODELS:
        avail = model_avail.get(m, False)
        model_rows.append({
            "Model": m,
            "Ollama Available": "✅ Yes" if avail else "❌ No",
            "Status": "Ready" if avail else "Pull required (`ollama pull " + m + "`)",
        })
    st.dataframe(pd.DataFrame(model_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# 2. EXPERIMENT LEADERBOARD & CHARTS (only if results exist)
# ==========================================
if not filtered_exps:
    st.info("No executed experiments match the current filters. The plan above shows all 36 configurations.")
    st.stop()

# Build primary comparison dataframe
data = []
for exp in filtered_exps:
    c = exp.config
    data.append({
        "Experiment ID": exp.experiment_id,
        "Timestamp": exp.timestamp[:16].replace("T", " "),
        "Model": c.model,
        "RAG Mode": c.rag_mode,
        "Split": c.dataset_split,
        "Repository": c.repository if c.repository else "all",
        "Cases": exp.total_cases_analyzed,
        "Accuracy": fmt_val(exp.accuracy, is_pct=True),
        "Precision": fmt_val(exp.precision),
        "Recall": fmt_val(exp.recall),
        "F1 Score": fmt_val(exp.f1_score),
        "FPR": fmt_val(exp.false_positive_rate),
        "Ev. Accuracy": fmt_val(exp.evidence_accuracy, is_pct=True),
        "Latency (s)": round(exp.avg_latency_s, 2) if exp.avg_latency_s else 0.0,
        "Status": exp.status,
        "Run Type": "Smoke Test" if getattr(c, "debug_sample_mode", False) else "Official",
    })

df = pd.DataFrame(data)

st.subheader("Executed Experiment Results")
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# Chart data (valid numerical F1 only)
valid_chart_data = []
for exp in filtered_exps:
    if exp.f1_score is not None:
        valid_chart_data.append({
            "Experiment ID": exp.experiment_id,
            "Model": exp.config.model,
            "RAG Mode": exp.config.rag_mode,
            "Split": exp.config.dataset_split,
            "F1 Score": float(exp.f1_score),
            "Precision": float(exp.precision) if exp.precision is not None else 0.0,
            "Recall": float(exp.recall) if exp.recall is not None else 0.0,
            "FPR": float(exp.false_positive_rate) if exp.false_positive_rate is not None else 0.0,
            "Latency (s)": float(exp.avg_latency_s) if exp.avg_latency_s else 0.0,
            "Cases": exp.total_cases_analyzed
        })

if valid_chart_data:
    chart_df = pd.DataFrame(valid_chart_data)
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Metric Comparison by Experiment")
        metrics = ["F1 Score", "Precision", "Recall", "FPR", "Latency (s)"]
        selected_metric = st.selectbox("Select Metric", metrics, index=0)
        
        bar_chart = alt.Chart(chart_df).mark_bar().encode(
            x=alt.X('Experiment ID:N', title='Experiment ID', sort='-y'),
            y=alt.Y(f'{selected_metric}:Q', title=selected_metric),
            color='Model:N',
            tooltip=['Experiment ID', 'Model', 'RAG Mode', 'Split', selected_metric, 'Cases']
        ).properties(height=350).interactive()
        st.altair_chart(bar_chart, use_container_width=True)
        
    with c2:
        st.subheader("Latency vs F1 Trade-off")
        scatter_lat = alt.Chart(chart_df).mark_circle(size=140).encode(
            x=alt.X('Latency (s):Q', title='Latency (seconds/case)'),
            y=alt.Y('F1 Score:Q', title='F1 Score'),
            color='Model:N',
            shape='RAG Mode:N',
            tooltip=['Experiment ID', 'Model', 'RAG Mode', 'Split', 'Latency (s)', 'F1 Score', 'Cases']
        ).properties(height=350).interactive()
        st.altair_chart(scatter_lat, use_container_width=True)

# ==========================================
# 3. RAG VS NON-RAG COMPARISON (Req #15)
# ==========================================
st.markdown("---")
st.header("⚖️ RAG vs. Non-RAG Head-to-Head Comparison")
st.markdown("Comparing retrieval-augmented reasoning against zero-context baseline across identical models and splits.")

rag_pairs = []
# Group by (Model, Split, Repository)
groups = {}
for e in filtered_exps:
    key = (e.config.model, e.config.dataset_split, e.config.repository)
    groups.setdefault(key, {})[e.config.rag_mode] = e

for (model, split, repo), modes in groups.items():
    if "Non-RAG" in modes and "RAG" in modes:
        base = modes["Non-RAG"]
        rag = modes["RAG"]
        rag_pairs.append({
            "Model": model,
            "Split": split,
            "Repository": repo if repo else "all",
            "Baseline F1": fmt_val(base.f1_score),
            "RAG F1": fmt_val(rag.f1_score),
            "Baseline FPR": fmt_val(base.false_positive_rate),
            "RAG FPR": fmt_val(rag.false_positive_rate),
            "Baseline Latency (s)": round(base.avg_latency_s, 2),
            "RAG Latency (s)": round(rag.avg_latency_s, 2),
            "Baseline Cases": base.total_cases_analyzed,
            "RAG Cases": rag.total_cases_analyzed,
        })

if rag_pairs:
    rag_df = pd.DataFrame(rag_pairs)
    st.dataframe(rag_df, use_container_width=True, hide_index=True)
else:
    st.info("To see direct RAG vs. Non-RAG comparisons, run both 'Non-RAG' and 'RAG' modes with the same model and split.")

# ==========================================
# 4. FULL EXPERIMENT RESULTS (Req #16)
# ==========================================
st.markdown("---")
st.header("📋 FULL EXPERIMENT RESULTS")
st.markdown("Complete experimental record: operational status, breakdowns by repository, language, drift type, and case-level audit trails.")

tab_overview, tab_matrix, tab_repos, tab_models, tab_drifttypes, tab_cases = st.tabs([
    "Overview", "Experiment Matrix", "Repository Results", "Model Results by Split", "Drift Type Results", "Case-Level Audit Trail"
])

# TAB 1: OVERVIEW
with tab_overview:
    st.subheader("Experimental Execution Overview")
    total_runs = len(filtered_exps)
    completed_runs = sum(1 for e in filtered_exps if e.status == "COMPLETED")
    failed_runs = sum(1 for e in filtered_exps if "FAILED" in e.status)
    unavailable_runs = sum(1 for e in filtered_exps if "UNAVAILABLE" in e.status)
    total_evaluated_cases = sum(e.total_cases_analyzed for e in filtered_exps)
    distinct_repos = len(set(e.config.repository for e in filtered_exps))
    from app.config import SUPPORTED_MODELS
    distinct_models_cnt = len(SUPPORTED_MODELS)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Actual Official Experiments", total_runs)
        st.metric("Total Cases Evaluated", total_evaluated_cases)
    with col2:
        st.metric("Completed Runs", completed_runs)
        st.metric("Unique Repositories", distinct_repos)
    with col3:
        st.metric("Failed / Incomplete Runs", failed_runs)
        st.metric("Configured Models", distinct_models_cnt)
    with col4:
        st.metric("Model Unavailable Runs", unavailable_runs)
        st.metric("Base Experiment Configurations", len(SUPPORTED_MODELS) * 3 * 2)

# TAB 2: EXPERIMENT MATRIX
with tab_matrix:
    st.subheader("Complete Experiment Matrix")
    matrix_rows = []
    for e in filtered_exps:
        c = e.config
        matrix_rows.append({
            "Experiment ID": e.experiment_id,
            "Model": c.model,
            "Split": c.dataset_split,
            "Repository": c.repository if c.repository else "all",
            "RAG": c.rag_mode,
            "Top-K": str(c.top_k) if c.rag_mode != "Non-RAG" else "N/A",
            "Prompt": c.prompt_version,
            "Cases Analyzed": e.total_cases_analyzed,
            "Completed": e.total_completed if e.total_completed else e.total_cases_analyzed,
            "Failed": e.total_failed,
            "Accuracy": fmt_val(e.accuracy, is_pct=True),
            "Precision": fmt_val(e.precision),
            "Recall": fmt_val(e.recall),
            "F1": fmt_val(e.f1_score),
            "FPR": fmt_val(e.false_positive_rate),
            "Latency (s)": round(e.avg_latency_s, 2),
            "Status": e.status,
            "Run Type": "Smoke Test" if getattr(c, "debug_sample_mode", False) else "Official"
        })
    st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

# TAB 3: REPOSITORY RESULTS
with tab_repos:
    st.subheader("Repository-Level Performance")
    repo_rows = []
    for e in filtered_exps:
        if e.repository_metrics:
            for repo_name, rmet in e.repository_metrics.items():
                repo_rows.append({
                    "Repository": repo_name,
                    "Language": rmet.get("language", "N/A"),
                    "Split": e.config.dataset_split,
                    "Model": e.config.model,
                    "RAG": e.config.rag_mode,
                    "Cases": rmet.get("cases", 0),
                    "Accuracy": fmt_val(rmet.get("accuracy"), is_pct=True),
                    "Precision": fmt_val(rmet.get("precision")),
                    "Recall": fmt_val(rmet.get("recall")),
                    "F1": fmt_val(rmet.get("f1")),
                })
    if repo_rows:
        st.dataframe(pd.DataFrame(repo_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No repository breakdowns stored for the filtered experiments yet.")

# TAB 4: MODEL RESULTS BY SPLIT
with tab_models:
    st.subheader("Model Performance by Dataset Split")
    split_summary = {}
    from app.config import SUPPORTED_MODELS
    for m in SUPPORTED_MODELS:
        for r in ["Non-RAG", "RAG"]:
            split_summary[(m, r)] = {"Train F1": "N/A", "Val F1": "N/A", "Test F1": "N/A", "Total Cases": 0}
            
    for e in filtered_exps:
        k = (e.config.model, e.config.rag_mode)
        if k in split_summary:
            split = e.config.dataset_split.capitalize()
            val = fmt_val(e.f1_score)
            if "Train" in split:
                split_summary[k]["Train F1"] = val
            elif "Val" in split:
                split_summary[k]["Val F1"] = val
            elif "Test" in split:
                split_summary[k]["Test F1"] = val
            split_summary[k]["Total Cases"] += e.total_cases_analyzed

    model_split_rows = []
    for (m, r), s in split_summary.items():
        # Only show models that are selected in the sidebar
        if m in selected_models and r in selected_rag:
            model_split_rows.append({
                "Model": m,
                "RAG Mode": r,
                "Train F1": s["Train F1"],
                "Validation F1": s["Val F1"],
                "Test F1": s["Test F1"],
                "Overall Cases Evaluated": s["Total Cases"]
            })
    st.dataframe(pd.DataFrame(model_split_rows), use_container_width=True, hide_index=True)

# TAB 5: DRIFT TYPE RESULTS
with tab_drifttypes:
    st.subheader("Performance by Drift Category")
    type_rows = []
    for e in filtered_exps:
        if e.drift_type_metrics:
            for dt, dmet in e.drift_type_metrics.items():
                type_rows.append({
                    "Drift Type": dt,
                    "Experiment ID": e.experiment_id,
                    "Model": e.config.model,
                    "RAG": e.config.rag_mode,
                    "Cases": dmet.get("cases", 0),
                    "Precision": fmt_val(dmet.get("precision")),
                    "Recall": fmt_val(dmet.get("recall")),
                    "F1 Score": fmt_val(dmet.get("f1")),
                })
    if type_rows:
        st.dataframe(pd.DataFrame(type_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No drift-type breakdowns stored for the filtered experiments yet.")

# TAB 6: CASE-LEVEL AUDIT TRAIL (Req #16, #17, #21)
with tab_cases:
    st.subheader("🔍 Case-Level Result Explorer & Execution Trace")
    
    exp_options = {e.experiment_id: f"{e.experiment_id} ({e.config.model} - {e.config.rag_mode} - {e.config.dataset_split})" for e in filtered_exps}
    selected_exp_id = st.selectbox("Select Experiment to Inspect", list(exp_options.keys()), format_func=lambda x: exp_options[x])
    
    if selected_exp_id:
        cases = runner.get_experiment_cases(selected_exp_id)
        if not cases:
            st.info(f"No individual case records found for experiment {selected_exp_id}.")
        else:
            st.markdown(f"**Loaded {len(cases)} cases for `{selected_exp_id}`**")
            
            # Error category filter
            classification_types = sorted(list(set(
                c.get("evaluation", {}).get("classification") or c.get("execution_status") or "UNKNOWN"
                for c in cases
            )))
            selected_class_filter = st.multiselect("Filter by Classification / Error Status", classification_types, default=classification_types)
            
            filtered_cases = [
                c for c in cases
                if (c.get("evaluation", {}).get("classification") or c.get("execution_status") or "UNKNOWN") in selected_class_filter
            ]
            
            # Summary Table
            case_table_data = []
            for c in filtered_cases:
                pred = c.get("parsed_prediction") or {}
                gt = c.get("ground_truth") or {}
                ev = c.get("evaluation") or {}
                
                case_table_data.append({
                    "Case ID": c.get("case_id"),
                    "Repository": c.get("repository"),
                    "Split": c.get("dataset_split"),
                    "Ground Truth": "DRIFT" if gt.get("drift_present") else "NO DRIFT",
                    "Prediction": "DRIFT" if pred.get("drift_present") else "NO DRIFT",
                    "Predicted Type": pred.get("drift_type", "N/A"),
                    "Classification": ev.get("classification", c.get("execution_status")),
                    "Verification": c.get("verification_status", "N/A"),
                    "Latency (s)": round(c.get("latency_s", 0.0), 2)
                })
                
            st.dataframe(pd.DataFrame(case_table_data), use_container_width=True, hide_index=True)
            
            st.markdown("### Case Drill-Down (End-to-End Audit Trace)")
            case_ids = [c.get("case_id") for c in filtered_cases]
            selected_case_id = st.selectbox("Pick a Case ID to View Full Trace", case_ids)
            
            if selected_case_id:
                chosen_case = next((c for c in filtered_cases if c.get("case_id") == selected_case_id), None)
                if chosen_case:
                    pred = chosen_case.get("parsed_prediction") or {}
                    gt = chosen_case.get("ground_truth") or {}
                    ev = chosen_case.get("evaluation") or {}
                    
                    st.markdown(f"#### 🔎 Audit Trace for `{selected_case_id}`")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown(f"**Repository:** `{chosen_case.get('repository')}`")
                        st.markdown(f"**Commit:** `{chosen_case.get('commit_sha')}`")
                        st.markdown(f"**Language:** `{chosen_case.get('language')}`")
                    with col_b:
                        st.markdown(f"**Artifact 1:** `{chosen_case.get('artifact_1_path')}` (`{chosen_case.get('artifact_1_type')}`)")
                        st.markdown(f"**Artifact 2:** `{chosen_case.get('artifact_2_path')}` (`{chosen_case.get('artifact_2_type')}`)")
                    with col_c:
                        st.markdown(f"**Execution Status:** `{chosen_case.get('execution_status')}`")
                        st.markdown(f"**Classification:** `{ev.get('classification')}`")
                        st.markdown(f"**Latency:** `{chosen_case.get('latency_s'):.2f}s`")
                        
                    st.markdown("---")
                    
                    # Detailed accordions for full auditability
                    with st.expander("1. Ground Truth & Dataset Definition", expanded=True):
                        st.json(gt)
                        
                    with st.expander("2. Retrieved Context (RAG Mode)"):
                        rc = chosen_case.get("retrieved_context")
                        if rc:
                            st.code(rc, language="markdown")
                        else:
                            st.info("No RAG context was retrieved for this case (Non-RAG mode or empty retrieval).")
                            
                    with st.expander("3. Exact Prompt Sent to LLM"):
                        st.code(chosen_case.get("prompt", "[No prompt saved]"), language="markdown")
                        
                    with st.expander("4. Raw LLM Output"):
                        st.code(chosen_case.get("raw_output", "[No raw output saved]"), language="json")
                        
                    with st.expander("5. Parsed Prediction & Verified Evidence", expanded=True):
                        st.markdown(f"**Verification Status:** `{chosen_case.get('verification_status')}`")
                        st.markdown(f"**Verification Details:** {chosen_case.get('verification_details')}")
                        st.json(pred)
