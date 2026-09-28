import streamlit as st
import pandas as pd
from pathlib import Path
from app.experiments.runner import ExperimentRunner

st.title("📄 Evaluation Report")
st.markdown("Comprehensive evaluation summary of DriftGuard runs.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

experiments = st.session_state.runner.get_experiments()

if not experiments:
    st.info("No experiments found. Run experiments to generate the evaluation report.")
    st.stop()
    
st.markdown("### Executive Summary")

total_runs = len(experiments)
avg_f1 = sum(e.f1_score for e in experiments) / total_runs if total_runs > 0 else 0
total_cases = sum(e.total_cases_analyzed for e in experiments)

c1, c2, c3 = st.columns(3)
c1.metric("Total Experiments", total_runs)
c2.metric("Total Cases Analyzed", total_cases)
c3.metric("Average F1 Score", f"{avg_f1:.3f}")

st.markdown("---")

for exp in experiments:
    with st.expander(f"Report: {exp.experiment_id} ({exp.config.model})"):
        st.markdown(f"**Timestamp:** {exp.timestamp}")
        st.markdown(f"**Repository:** {exp.config.repository}")
        st.markdown(f"**Dataset Split:** {exp.config.dataset_split}")
        st.markdown(f"**Analysis Mode:** {exp.config.rag_mode}")
        
        st.markdown("#### Performance Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("F1 Score", f"{exp.f1_score:.3f}")
        m2.metric("Precision", f"{exp.precision:.3f}")
        m3.metric("Recall", f"{exp.recall:.3f}")
        m4.metric("False Positive Rate", f"{exp.false_positive_rate:.3f}")
        
        st.markdown(f"- **Total Cases Analyzed:** {exp.total_cases_analyzed}")
        st.markdown(f"- **Average Latency:** {exp.avg_latency_s:.2f}s")
        
        st.download_button(
            label="Download JSON Report",
            data=exp.to_json(),
            file_name=f"{exp.experiment_id}_report.json",
            mime="application/json",
            key=f"dl_{exp.experiment_id}"
        )
