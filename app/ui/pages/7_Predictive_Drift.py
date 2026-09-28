import streamlit as st
import pandas as pd
import json
from pathlib import Path
from collections import Counter
from app.experiments.runner import ExperimentRunner

st.title("🔮 Predictive Drift Analysis")
st.markdown("Identify files and artifacts most susceptible to drift based on historical experiment data.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

experiments = st.session_state.runner.get_experiments()

if not experiments:
    st.info("No experiments found. Run experiments to generate predictive insights.")
    st.stop()

file_drifts = Counter()
drift_types = Counter()

for exp in experiments:
    if exp.total_cases_analyzed > 0:
        run_dir = Path("results/experiments") / exp.experiment_id
        reports_file = run_dir / "reports.jsonl"
        
        if reports_file.exists():
            with open(reports_file, 'r') as f:
                for line in f:
                    r = json.loads(line)
                    if r.get('prediction') and r['prediction'].get('drift_present'):
                        # Only count confirmed drifts — not hallucinated/unverified ones
                        status = r.get('verification_status', 'No Drift')
                        if status == 'Confirmed Drift':
                            file_drifts[r['artifact_1_path']] += 1
                            file_drifts[r['artifact_2_path']] += 1
                            drift_types[r['prediction']['drift_type']] += 1

if not file_drifts:
    st.success("No verified drift history found to predict future vulnerabilities.")
    st.stop()

st.subheader("Top Drift Vulnerable Files")
data = [{"File Path": path, "Drift Occurrences": count} for path, count in file_drifts.most_common(20)]
df = pd.DataFrame(data)

c1, c2 = st.columns([2, 1])

with c1:
    import altair as alt
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Drift Occurrences:Q', title='Occurrences'),
        y=alt.Y('File Path:N', sort='-x', title='File'),
        tooltip=['File Path', 'Drift Occurrences']
    ).properties(height=500).interactive()
    st.altair_chart(chart, use_container_width=True)

with c2:
    st.dataframe(df, hide_index=True)

st.markdown("---")
st.subheader("Frequent Drift Types")
type_data = [{"Drift Type": t, "Count": c} for t, c in drift_types.most_common()]
st.dataframe(pd.DataFrame(type_data), hide_index=True, use_container_width=True)
