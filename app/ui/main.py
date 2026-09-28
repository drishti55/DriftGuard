"""
DriftGuard Main UI Entry Point
Configures the multi-page navigation for the application.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.session import init_session_state

st.set_page_config(
    page_title="DriftGuard — AI Drift Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def render_sidebar():
    st.sidebar.markdown("## 🛡️ DriftGuard")
    st.sidebar.markdown("*AI Software Drift Platform*")
    st.sidebar.markdown("---")

def main():
    init_session_state()
    render_sidebar()
    
    pages = {
        "Core": [
            st.Page("pages/1_Overview.py", title="Overview", icon="🏠"),
            st.Page("pages/2_Drift_Explorer.py", title="Drift Explorer", icon="🔍"),
        ],
        "Research & Lab": [
            st.Page("pages/3_Experiment_Lab.py", title="Experiment Lab", icon="🧪"),
            st.Page("pages/4_Model_Comparison.py", title="Model Comparison", icon="📊"),
            st.Page("pages/5_Evidence_Lab.py", title="Evidence Lab", icon="📋"),
        ],
        "Advanced Analysis": [
            st.Page("pages/6_Dependency_Graph.py", title="Drift Graph", icon="🕸️"),
            st.Page("pages/7_Predictive_Drift.py", title="Predictive Drift", icon="🔮"),
        ],
        "System": [
            st.Page("pages/8_Evaluation_Report.py", title="Evaluation Report", icon="📑"),
            st.Page("pages/9_Settings.py", title="Settings", icon="⚙️"),
        ]
    }
    
    pg = st.navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()
