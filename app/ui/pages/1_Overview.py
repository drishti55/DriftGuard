import streamlit as st
import tempfile
import os

def handle_ingestion():
    """Step 1 & 2: Repository Source Input and Scanning"""
    st.header("Step 1: Select Repository Source")
    
    tab1, tab2, tab3 = st.tabs(["GitHub URL", "ZIP/Tar Upload", "Local Path"])
    
    with tab1:
        repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/owner/repo")
        branch = st.text_input("Branch (optional)", placeholder="main")
        if st.button("Clone & Scan"):
            if not repo_url:
                st.error("Please enter a valid URL.")
                return
            with st.spinner(f"Cloning {repo_url}..."):
                try:
                    repo = st.session_state.ingestor.ingest_from_github(repo_url, branch if branch else None)
                    _process_ingested_repo(repo)
                except Exception as e:
                    st.error(f"Error cloning repository: {e}")

    with tab2:
        uploaded_file = st.file_uploader("Upload Repository Archive (.zip, .tar.gz)", type=["zip", "tar.gz", "tar", "tgz"])
        if uploaded_file and st.button("Extract & Scan"):
            with st.spinner("Extracting archive safely..."):
                try:
                    # Save to temp file
                    fd, temp_path = tempfile.mkstemp(suffix=f".{uploaded_file.name.split('.')[-1]}")
                    with os.fdopen(fd, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    repo = st.session_state.ingestor.ingest_from_archive(temp_path)
                    os.unlink(temp_path) # remove the archive
                    _process_ingested_repo(repo)
                except Exception as e:
                    st.error(f"Error extracting repository: {e}")

    with tab3:
        local_path = st.text_input("Local Directory Path", placeholder="/Users/username/projects/my-repo")
        if st.button("Scan Local Path"):
            if not local_path or not os.path.isdir(local_path):
                st.error("Please enter a valid directory path.")
                return
            with st.spinner(f"Scanning local directory {local_path}..."):
                try:
                    repo = st.session_state.ingestor.ingest_from_local(local_path)
                    _process_ingested_repo(repo)
                except Exception as e:
                    st.error(f"Error loading local path: {e}")


def _process_ingested_repo(repo):
    """Scan the repo and update session state."""
    st.session_state.ingested_repo = repo
    scanner = st.session_state.scanner
    info = scanner.scan(repo)
    st.session_state.repo_info = info
    st.session_state.reports = []
    st.rerun()


def render_repository_overview():
    """Step 2: Repository Overview"""
    if not st.session_state.repo_info:
        return
        
    info = st.session_state.repo_info
    repo = st.session_state.ingested_repo

    st.header("Step 2: Repository Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**Source**: `{repo.source_type.title()}`")
        st.markdown(f"**Target**: `{repo.original_source.split('/')[-1]}`")
    with col2:
        st.markdown(f"**Language**: `{info.language}`")
        st.markdown(f"**Commit**: `{info.commit_sha[:8] if info.commit_sha else 'N/A'}`")
    with col3:
        st.markdown(f"**Artifacts Discovered**: `{len(info.artifacts)}`")
    with col4:
        if st.button("Cancel & Load New", type="secondary"):
            if repo.cleanup_func:
                repo.cleanup()
            st.session_state.ingested_repo = None
            st.session_state.repo_info = None
            st.session_state.reports = []
            st.rerun()

    st.markdown("### Artifact Breakdown")
    type_counts = info.artifact_type_counts
    
    # Display breakdown as pills/badges
    badges = " ".join([f"`{t}: {c}`" for t, c in type_counts.items()])
    st.markdown(badges)
    
    st.markdown("---")
    st.markdown("### Ready for Analysis")
    st.info("The repository is loaded. Go to the **Drift Explorer** to run an analysis or the **Experiment Lab** to configure research runs.")

def render_diagnostics():
    """Renders the diagnostic panel showing pipeline health."""
    st.markdown("### 🩺 Pipeline Health & Diagnostics")
    
    from app.config import SPLITS_DIR
    from app.experiments.runner import ExperimentRunner
    from app.analysis.llm_client import LLMClient
    
    # 1. Dataset stats
    train_file = SPLITS_DIR / "train.jsonl"
    test_file = SPLITS_DIR / "test.jsonl"
    val_file = SPLITS_DIR / "validation.jsonl"
    
    def count_cases(file_path):
        if not file_path.exists(): return 0
        try:
            with open(file_path, "r") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
            
    train_cases = count_cases(train_file)
    test_cases = count_cases(test_file)
    val_cases = count_cases(val_file)
    total_cases = train_cases + test_cases + val_cases
    dataset_status = "PASS" if total_cases > 0 else "FAIL"
    
    # 2. Models
    try:
        import ollama
        models = ollama.list().models
        model_count = len(models)
    except Exception:
        model_count = 0
        
    # 3. Experiments
    from pathlib import Path
    runner = ExperimentRunner(Path("results/experiments"))
    exps = runner.get_experiments()
    completed = [e for e in exps if e.f1_score is not None]
    failed = [e for e in exps if e.f1_score is None]
    
    total_evals = sum(e.total_cases_analyzed for e in exps)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Dataset Loaded**: `{dataset_status}`")
        st.markdown(f"**Cases Found**: `{total_cases}`")
        st.markdown(f"**Models Available**: `{model_count}`")
    with c2:
        st.markdown(f"**Experiments Found**: `{len(exps)}`")
        st.markdown(f"**Completed Results**: `{len(completed)}`")
        st.markdown(f"**Failed/Empty Results**: `{len(failed)}`")
    with c3:
        st.markdown(f"**Evaluation Cases Run**: `{total_evals}`")
        if st.session_state.get('repo_info'):
            st.markdown(f"**Artifacts Parsed**: `{len(st.session_state.repo_info.artifacts)}`")
        else:
            st.markdown(f"**Artifacts Parsed**: `N/A`")
            
    st.markdown("---")


st.title("🏠 Overview")

render_diagnostics()

if not st.session_state.get("ingested_repo"):
    handle_ingestion()
else:
    render_repository_overview()
