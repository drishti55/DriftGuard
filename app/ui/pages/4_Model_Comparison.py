import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from app.experiments.runner import ExperimentRunner

st.title("📊 Model & Pipeline Comparison")
st.markdown("Compare results across different experiment runs.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

experiments = st.session_state.runner.get_experiments()

if not experiments:
    st.info("No experiments found. Go to the Experiment Lab to run some analyses.")
    st.stop()

# Build comparison dataframe
data = []
for exp in experiments:
    c = exp.config
    cases = exp.total_cases_analyzed
    
    # Format metrics: N/A if None (e.g. 0 cases evaluated)
    f1 = exp.f1_score if exp.f1_score is not None else "N/A"
    prec = exp.precision if exp.precision is not None else "N/A"
    rec = exp.recall if exp.recall is not None else "N/A"
    fpr = exp.false_positive_rate if exp.false_positive_rate is not None else "N/A"
    
    data.append({
        "ID": exp.experiment_id,
        "Timestamp": exp.timestamp[:16].replace("T", " "),
        "Model": c.model,
        "RAG Mode": c.rag_mode,
        "Dataset": c.dataset_split,
        "F1 Score": f1,
        "Precision": prec,
        "Recall": rec,
        "FPR": fpr,
        "Ev. Accuracy": exp.evidence_accuracy if exp.evidence_accuracy is not None else "N/A",
        "Latency (s)": exp.avg_latency_s,
        "Cases Analyzed": cases
    })

df = pd.DataFrame(data)

st.subheader("Experiment Results Table")
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# Filter out rows with "N/A" for charts
valid_df = df[df["F1 Score"] != "N/A"].copy()

if len(valid_df) == 0:
    st.info("No valid performance metrics to display in charts. This usually means the dataset had 0 cases evaluated.")
elif len(valid_df) > 0:
    st.subheader("Metrics by Model")
    
    metrics = ["F1 Score", "Precision", "Recall", "FPR", "Latency (s)"]
    selected_metric = st.selectbox("Select Metric to Visualize", metrics)
    
    # Altair bar chart grouped by model
    chart = alt.Chart(valid_df).mark_bar().encode(
        x=alt.X('Model:N', title='Model'),
        y=alt.Y(f'{selected_metric}:Q', title=selected_metric),
        color='Dataset:N',
        tooltip=['ID', 'Model', 'Dataset', selected_metric, 'Cases Analyzed']
    ).properties(
        width=600,
        height=400,
        title=f"{selected_metric} Comparison"
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Error Analysis (FPR vs Recall)")
        scatter = alt.Chart(valid_df).mark_circle(size=100).encode(
            x='FPR:Q',
            y='Recall:Q',
            color='Model:N',
            tooltip=['ID', 'Model', 'FPR', 'Recall']
        ).interactive()
        st.altair_chart(scatter, use_container_width=True)
        
    with c2:
        st.subheader("Latency vs F1 Score")
        scatter_latency = alt.Chart(valid_df).mark_circle(size=100).encode(
            x='Latency (s):Q',
            y='F1 Score:Q',
            color='Model:N',
            tooltip=['ID', 'Model', 'Latency (s)', 'F1 Score']
        ).interactive()
        st.altair_chart(scatter_latency, use_container_width=True)
else:
    st.info("Run more than one experiment to see rich comparison charts.")
