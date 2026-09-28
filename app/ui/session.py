import streamlit as st

def init_session_state():
    """Initialize Streamlit session state globally."""
    from app.ingestion.repository_ingestor import RepositoryIngestor
    from app.ingestion.repository_scanner import RepositoryScanner

    defaults = {
        "ingested_repo": None,
        "repo_info": None,
        "reports": [],
        "reports_b": [],
        "analysis_running": False,
        "ingestor": RepositoryIngestor(),
        "scanner": RepositoryScanner(),
        "model_a_name": None,
        "model_b_name": None,
        "analysis_mode": "single",
        "experiment_id": None,
        "selected_finding": None,
        "rag_config": None,
        "retrieval_config": None,
        "current_commit": None,
        "selected_repo": None,
        "benchmark_results": None,
        "comparison_results": None,
        "dataset_split": "test",
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
