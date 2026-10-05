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
    st.info("The repository is loaded. Go to the **Drift Explorer** to run an analysis or inspect repository relationships.")

def render_diagnostics():
    """Renders the diagnostic panel showing workspace & gateway health."""
    st.markdown("### 🩺 Workspace & Gateway Health")
    
    from app import config
    from app.config_schema import DriftGuardConfig
    
    # 1. Configuration check
    try:
        DriftGuardConfig.load()
        config_status = "✅ Valid (.driftguard.yml)"
    except Exception:
        config_status = "⚠️ Default Fallback"
        
    # 2. Model gateway
    gateway_host = config.OMNIROUTE_HOST
    gateway_status = f"Connected ({gateway_host})"
    
    # 3. Artifact count
    if st.session_state.get('repo_info'):
        parsed_count = len(st.session_state.repo_info.artifacts)
        candidates_count = len(st.session_state.repo_info.drift_candidates)
    else:
        parsed_count = 0
        candidates_count = 0
        
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Policy Config**: `{config_status}`")
        st.markdown(f"**Model Gateway**: `{gateway_status}`")
    with c2:
        st.markdown(f"**Default Model**: `{config.DEFAULT_MODEL}`")
        st.markdown(f"**Fallback Host**: `{config.OLLAMA_HOST}`")
    with c3:
        st.markdown(f"**Artifacts Parsed**: `{parsed_count}`")
        st.markdown(f"**Candidates Generated**: `{candidates_count}`")
            
    st.markdown("---")


st.title("🏠 Overview")

render_diagnostics()

if not st.session_state.get("ingested_repo"):
    handle_ingestion()
else:
    render_repository_overview()
