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
            st.Page("pages/1_Overview.py", title="Repository Overview", icon="🏠"),
            st.Page("pages/2_Drift_Explorer.py", title="Drift Explorer", icon="🔍"),
        ],
        "Architecture": [
            st.Page("pages/3_Dependency_Graph.py", title="Dependency Graph", icon="🕸️"),
        ],
        "System": [
            st.Page("pages/4_Settings.py", title="Settings", icon="⚙️"),
        ]
    }
    
    pg = st.navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()
