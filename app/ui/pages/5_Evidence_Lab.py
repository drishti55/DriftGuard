import streamlit as st
import pandas as pd
import json
from pathlib import Path
from app.experiments.runner import ExperimentRunner

st.title("📋 Evidence Lab")
st.markdown("Analyze evidence verification across experiment runs — which drifts were confirmed vs discarded.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

experiments = st.session_state.runner.get_experiments()

if not experiments:
    st.info("No experiments found. Run experiments first to populate this dashboard.")
    st.stop()

# Build evidence data using the new three-state status system
data = []
for exp in experiments:
    if exp.total_cases_analyzed > 0:
        run_dir = Path("results/experiments") / exp.experiment_id
        reports_file = run_dir / "reports.jsonl"
        confirmed = 0
        no_drift = 0
        analysis_failed = 0
        total_pairs = 0

        if reports_file.exists():
            with open(reports_file, 'r') as f:
                for line in f:
                    r = json.loads(line)
                    total_pairs += 1
                    status = r.get('verification_status', 'No Drift')
                    if status == 'Confirmed Drift':
                        confirmed += 1
                    elif status == 'Analysis Failed':
                        analysis_failed += 1
                    else:
                        no_drift += 1

        data.append({
            "Experiment": exp.experiment_id,
            "Model": exp.config.model,
            "Pairs Analyzed": total_pairs,
            "Confirmed Drifts": confirmed,
            "No Drift": no_drift,
            "Analysis Failed": analysis_failed,
        })

if data:
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Verification Breakdown")
    import altair as alt

    melted = df.melt(
        id_vars=["Experiment", "Model"],
        value_vars=["Confirmed Drifts", "No Drift", "Analysis Failed"],
        var_name="Status", value_name="Count"
    )

    color_scale = alt.Scale(
        domain=["Confirmed Drifts", "No Drift", "Analysis Failed"],
        range=["#2ecc71", "#3498db", "#e74c3c"]
    )

    chart = alt.Chart(melted).mark_bar().encode(
        x=alt.X('Experiment:N', title='Experiment'),
        y=alt.Y('Count:Q', title='Count'),
        color=alt.Color('Status:N', scale=color_scale),
        tooltip=['Model', 'Status', 'Count']
    ).properties(height=400).interactive()

    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("No drift findings with verification data available yet.")
