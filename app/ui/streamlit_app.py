import streamlit as st
import sys
import os
import tempfile
import pandas as pd
from pathlib import Path
from typing import Optional

# Ensure the project root is in sys.path so 'app' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.ingestion.repository_ingestor import RepositoryIngestor
from app.ingestion.repository_scanner import RepositoryScanner
from app.analysis.llm_client import LLMClient
from app.analysis.drift_pipeline import DriftPipeline

# Required fields that a RepoInfo produced by the current RepositoryScanner must have.
# If a cached object is missing any of these (stale from old code), it is evicted.
_REQUIRED_REPO_INFO_FIELDS = ['scan_metrics', 'drift_candidates', 'artifact_type_counts', 'artifacts']
_REQUIRED_ARTIFACT_FIELDS = ['artifact_category', 'status', 'file_type']

def _is_repo_info_valid(info) -> bool:
    """
    Returns True only if the RepoInfo object was produced by the current scanner
    and has all required fields actually populated (not just structurally present).
    A RepoInfo is considered stale/invalid if:
    - It is missing any required attribute (old code path)
    - scan_metrics is empty dict (scanner crashed before populating it)
    - artifacts list has items but they lack artifact_category (pre-schema artifacts)
    """
    for field in _REQUIRED_REPO_INFO_FIELDS:
        if not hasattr(info, field):
            return False
    # scan_metrics must have at least 'files_discovered' to be from current scanner
    if not getattr(info, 'scan_metrics', None):
        return False
    if 'files_discovered' not in info.scan_metrics:
        return False
    # Spot-check the first artifact's schema
    artifacts = getattr(info, 'artifacts', [])
    if artifacts:
        first = artifacts[0]
        for field in _REQUIRED_ARTIFACT_FIELDS:
            if not hasattr(first, field):
                return False
    return True

def init_session_state():
    # Structural validation: evict any stale RepoInfo that was created by older code.
    # This is safer than a version number because it validates the actual data contract.
    if 'repo_info' in st.session_state and st.session_state.repo_info is not None:
        if not _is_repo_info_valid(st.session_state.repo_info):
            st.session_state.pop('repo_info', None)
            st.session_state.pop('pipeline_result', None)
            st.session_state.pop('reports', None)
            st.session_state.pop('analysis_running', None)
            # Keep ingested_repo so the user can re-trigger a scan without re-entering the URL

    if "ingestor" not in st.session_state:
        st.session_state.ingestor = RepositoryIngestor()
    if "scanner" not in st.session_state:
        st.session_state.scanner = RepositoryScanner()
    if "ingested_repo" not in st.session_state:
        st.session_state.ingested_repo = None
    if "repo_info" not in st.session_state:
        st.session_state.repo_info = None
    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None
    if "reports" not in st.session_state:
        st.session_state.reports = []
    if "analysis_running" not in st.session_state:
        st.session_state.analysis_running = False

def render_header():
    st.set_page_config(
        page_title="DriftGuard — Cross-Artifact Consistency Analyzer",
        page_icon="🛡️",
        layout="wide",
    )

    st.markdown("""
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1rem; color: #666; margin-bottom: 1.5rem; }
    .drift-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.2rem; margin: 0.8rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .evidence-box { background-color: #f8f9fa; border-left: 4px solid #1976d2; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.88em; white-space: pre-wrap; margin: 8px 0; }
    .metric-badge { background-color: #e3f2fd; color: #0d47a1; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="main-header">🛡️ DriftGuard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Cross-Artifact Consistency Analyzer</p>', unsafe_allow_html=True)

def handle_ingestion():
    """Step 1: Select Repository Source"""
    st.header("Step 1: Select Repository Source")
    tab1, tab2, tab3 = st.tabs(["Local Path", "GitHub URL", "ZIP/Tar Upload"])
    
    with tab1:
        local_path = st.text_input("Local Directory Path", placeholder="/Users/drishti/Desktop/Projects/BUGTRACE prj/driftguard-dataset/repositories/OT-CONTAINER-KIT_redis-operator")
        if st.button("Scan Local Repository", type="primary"):
            if not local_path or not os.path.isdir(local_path):
                st.error("Please enter a valid directory path.")
                return
            with st.spinner(f"Recursively scanning repository at {local_path}..."):
                try:
                    repo = st.session_state.ingestor.ingest_from_local(local_path)
                    _process_ingested_repo(repo)
                except Exception as e:
                    st.error(f"Error loading local path: {e}")

    with tab2:
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

    with tab3:
        uploaded_file = st.file_uploader("Upload Repository Archive (.zip, .tar.gz)", type=["zip", "tar.gz", "tar", "tgz"])
        if uploaded_file and st.button("Extract & Scan"):
            with st.spinner("Extracting archive safely..."):
                try:
                    fd, temp_path = tempfile.mkstemp(suffix=f".{uploaded_file.name.split('.')[-1]}")
                    with os.fdopen(fd, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    repo = st.session_state.ingestor.ingest_from_archive(temp_path)
                    os.unlink(temp_path)
                    _process_ingested_repo(repo)
                except Exception as e:
                    st.error(f"Error extracting repository: {e}")

def _process_ingested_repo(repo):
    """Run scanner, validate output, store in session state."""
    st.session_state.ingested_repo = repo
    scanner = st.session_state.scanner
    try:
        info = scanner.scan(repo)
    except Exception as e:
        st.error(f"Repository scan failed: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    # Validate the result before storing it
    if not _is_repo_info_valid(info):
        st.error(
            "Scanner returned an incomplete result. "
            f"scan_metrics={getattr(info, 'scan_metrics', 'MISSING')}. "
            "Check the Streamlit server logs for errors during scanning."
        )
        return
    st.session_state.repo_info = info
    st.session_state.reports = []
    st.session_state.pipeline_result = None
    st.rerun()

def render_repository_overview():
    """Step 2: Repository Overview and Scan Metrics"""
    if not st.session_state.repo_info:
        return
        
    info = st.session_state.repo_info
    repo = st.session_state.ingested_repo
    metrics = getattr(info, 'scan_metrics', None) or {}

    st.header("Step 2: Repository Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**Target**: `{repo.original_source.split('/')[-1]}`")
        st.markdown(f"**Source**: `{repo.source_type.title()}`")
    with col2:
        st.markdown(f"**Language**: `{info.language}`")
        st.markdown(f"**Framework**: `{info.framework}`")
    with col3:
        st.markdown(f"**Commit**: `{info.commit_sha[:8] if info.commit_sha else 'N/A'}`")
        st.markdown(f"**Package Mgr**: `{info.package_manager}`")
    with col4:
        if st.button("Cancel & Load New", type="secondary"):
            if repo.cleanup_func:
                repo.cleanup()
            st.session_state.ingested_repo = None
            st.session_state.repo_info = None
            st.session_state.reports = []
            st.session_state.pipeline_result = None
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Repository Scan Coverage")

    # All values come from scan_metrics produced by RepositoryScanner.scan().
    # If scan_metrics is missing a key the field shows "—" (not 0) so we never
    # silently convert a missing value into a false zero.
    def _metric_val(key: str):
        """Return the metric integer, or None (shown as '—') if not yet calculated."""
        return metrics.get(key)  # None when absent

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        v = _metric_val("files_discovered")
        st.metric("Files Discovered", v if v is not None else "—")
    with m2:
        v = _metric_val("relevant_artifacts")
        st.metric("Relevant Artifacts", v if v is not None else "—")
    with m3:
        v = _metric_val("ignored_vendor_cache")
        st.metric("Ignored (Vendor/Cache)", v if v is not None else "—")
    with m4:
        v = _metric_val("ignored_binary")
        st.metric("Ignored (Binaries)", v if v is not None else "—")
    with m5:
        v = _metric_val("candidates_generated")
        st.metric("Drift Candidates", v if v is not None else "—")

    st.markdown("### Relevant Artifact Breakdown")
    type_counts = getattr(info, 'artifact_type_counts', {})
    badges = " &nbsp; ".join([f"`{t}: {c}`" for t, c in type_counts.items()])
    st.markdown(badges if badges else "_No artifact type data available._")

def run_analysis(model: str, max_candidates: Optional[int]):
    """Execute analysis over candidate relationships."""
    info = st.session_state.repo_info
    repo = st.session_state.ingested_repo

    candidates = getattr(info, 'drift_candidates', None)
    if not candidates:
        # Show the full pipeline diagnostic so the user can see exactly where
        # the pipeline produced zero results — not a silent "no candidates" message.
        st.error("## ⚠️ PIPELINE DIAGNOSTIC: Zero Relationship Candidates Generated")
        st.markdown(
            "The repository was scanned and artifacts were classified, but the "
            "relationship engine found no verifiable cross-artifact relationships. "
            "This is NOT treated as 'No Drift Found' — it means the analysis could not run."
        )
        sm = info.scan_metrics
        artifacts = info.artifacts
        by_cat = {}
        for a in artifacts:
            cat = getattr(a, 'artifact_category', 'unknown')
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(a)

        st.markdown("### Repository Artifact Inventory")
        cols = st.columns(4)
        categories = ['source_code', 'test', 'documentation', 'dependency',
                      'ci_configuration', 'docker_configuration', 'deployment_configuration', 'other_configuration']
        for i, cat in enumerate(categories):
            count = len(by_cat.get(cat, []))
            cols[i % 4].metric(cat.replace('_', ' ').title(), count)

        st.markdown("### Relationship Engine Diagnosis")
        tests = by_cat.get('test', [])
        sources = by_cat.get('source_code', [])
        deps = by_cat.get('dependency', [])
        ci = by_cat.get('ci_configuration', [])
        docker = by_cat.get('docker_configuration', [])

        test_imports = sum(len(getattr(a, 'extracted_info', None).imports
                              if getattr(a, 'extracted_info', None) else []) for a in tests)
        src_imports = sum(len(getattr(a, 'extracted_info', None).imports
                             if getattr(a, 'extracted_info', None) else []) for a in sources)
        dep_pkgs = sum(len(getattr(a, 'extracted_info', None).dependencies
                           if getattr(a, 'extracted_info', None) else []) for a in deps)

        diag_data = [
            ("Test artifacts", len(tests)),
            ("Source artifacts", len(sources)),
            ("Imports extracted from tests", test_imports),
            ("Imports extracted from sources", src_imports),
            ("Dependency packages declared", dep_pkgs),
            ("CI artifacts", len(ci)),
            ("Docker artifacts", len(docker)),
            ("Relationships generated", sm.get("relationships_discovered", 0)),
            ("Candidates generated", sm.get("candidates_generated", 0)),
        ]
        for label, val in diag_data:
            icon = "✅" if val > 0 else "❌"
            st.markdown(f"{icon} **{label}:** `{val}`")

        if test_imports == 0 and src_imports == 0:
            st.error("**Root cause:** Fact extraction produced no imports from tests or source files. Check that the extractor supports this language.")
        elif len(sources) == 0:
            st.error("**Root cause:** No source code artifacts were classified. Check the file classifier.")
        elif len(tests) == 0 and len(deps) == 0 and len(ci) == 0:
            st.error("**Root cause:** No test, dependency, or CI artifacts found to pair with source code.")
        else:
            st.warning("**Root cause:** Relationship matching found no verifiable connections between classified artifacts. "
                       "The test-to-source name matching and import matching may not cover this repository's structure.")

        st.session_state.analysis_running = False
        return

    llm = LLMClient(model=model)
    pipeline = DriftPipeline(workspace_path=repo.workspace_path, llm_client=llm)

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, msg):
        progress_bar.progress(min(current / total, 1.0))
        status_text.markdown(f"**Status:** {msg}")

    result = pipeline.analyze_repository(
        repo_info=info,
        max_candidates=max_candidates,
        progress_callback=update_progress
    )

    st.session_state.pipeline_result = result
    st.session_state.reports = result["reports"]
    st.session_state.analysis_running = False
    status_text.success("Analysis complete!")
    st.rerun()

def render_analysis_configuration():
    """Step 3: Analysis Execution"""
    if not st.session_state.repo_info:
        return

    info = st.session_state.repo_info
    # candidates_generated comes from scan_metrics (produced by RepositoryScanner);
    # fall back to len(drift_candidates) if scan was done in same session.
    sm = getattr(info, 'scan_metrics', {}) or {}
    candidates_count = sm.get('candidates_generated', len(getattr(info, 'drift_candidates', [])))

    st.header("Step 3: Analysis Configuration")

    col1, col2 = st.columns(2)
    with col1:
        model = st.selectbox("LLM Reasoning Model", ["qwen2.5-coder:7b", "codellama:7b", "starcoder2:3b"])
    with col2:
        analysis_mode = st.radio(
            "Candidate Coverage",
            [f"Analyze All Candidates ({candidates_count})", "Run Initial Batch (First 50 Candidates)"],
            index=0
        )
        max_candidates = None if "Analyze All" in analysis_mode else 50

    if st.button("🚀 Run Repository Drift Analysis", type="primary", disabled=st.session_state.analysis_running):
        st.session_state.analysis_running = True
        run_analysis(model, max_candidates)

def render_reports():
    """Step 4: Drift Reports & Verification"""
    result = st.session_state.pipeline_result
    reports = st.session_state.reports
    if not reports or not result:
        return

    st.markdown("---")
    st.header("Step 4: Drift Analysis Results")

    metrics = result.get("metrics", {})
    status = result.get("status", "NO DRIFT FOUND")
    confirmed_drifts = result.get("confirmed_drifts", [])
    analyzed_count = metrics.get("candidates_analyzed", len(reports))
    total_candidates = metrics.get("candidates_generated", len(reports))

    # Display Metrics Summary Box
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Candidates Generated", total_candidates)
    with col2:
        st.metric("Candidates Analyzed", analyzed_count)
    with col3:
        st.metric("Candidates Verified", metrics.get("candidates_verified", analyzed_count))
    with col4:
        st.metric("Confirmed Drifts", len(confirmed_drifts))

    st.markdown("---")

    # Hard safety invariant outcomes
    if status == "DRIFT DETECTED" or len(confirmed_drifts) > 0:
        st.error(f"## 🚨 DRIFT DETECTED ({len(confirmed_drifts)} confirmed)")
        st.markdown(f"Verified contradiction across **{analyzed_count}** analyzed relationship candidates.")

        for idx, r in enumerate(confirmed_drifts):
            pred = r.prediction
            type_label = pred.drift_type.replace('_', ' ').title() if pred else "Cross Artifact"
            lines_1 = getattr(pred, 'file_1_lines', None) or getattr(pred, 'artifact_1_lines', None) or "N/A"
            lines_2 = getattr(pred, 'file_2_lines', None) or getattr(pred, 'artifact_2_lines', None) or "N/A"

            with st.container():
                st.markdown(f'<div class="drift-card">', unsafe_allow_html=True)
                st.markdown(f"### DRIFT {idx + 1:02d} — {type_label}")
                st.markdown(f"**File 1:** `{r.artifact_1_path}` (Lines {lines_1})")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**vs**")
                st.markdown(f"**File 2:** `{r.artifact_2_path}` (Lines {lines_2})")

                ev1 = getattr(r, 'real_evidence_1', '') or getattr(pred, 'extracted_fact_1', '') or "[Not extracted]"
                ev2 = getattr(r, 'real_evidence_2', '') or getattr(pred, 'extracted_fact_2', '') or "[Not extracted]"
                
                st.markdown(f'<div class="evidence-box"><b>[Evidence from {Path(r.artifact_1_path).name}]:</b>\n{ev1}\n\n<b>[Evidence from {Path(r.artifact_2_path).name}]:</b>\n{ev2}</div>', unsafe_allow_html=True)
                
                contradiction = getattr(pred, 'contradiction_rationale', '') or getattr(pred, 'evidence', '')
                st.markdown(f"**Why this is a contradiction:** {contradiction}")
                st.markdown('</div>', unsafe_allow_html=True)

    elif status == "ANALYSIS INCOMPLETE":
        remaining = metrics.get("candidates_remaining", total_candidates - analyzed_count)
        st.warning(f"## ⚠️ ANALYSIS INCOMPLETE")
        st.markdown(f"**Candidates Analyzed:** `{analyzed_count}` &nbsp;|&nbsp; **Candidates Remaining:** `{remaining}`")
        st.info("DriftGuard does not infer 'No Drift' from a partial repository scan. Run all remaining candidates for a complete guarantee.")

    else:
        st.success("## ✅ NO DRIFT FOUND")
        st.markdown(f"The analyzed repository is **consistent across all {analyzed_count} checked relationship candidates**.")
        checked_categories = sorted({r.artifact_1_type for r in reports} | {r.artifact_2_type for r in reports})
        st.info(f"Verified categories: {', '.join(c.replace('_', ' ').title() for c in checked_categories)}")

def render_file_analysis_view():
    """Step 5: Complete Repository File Inventory View"""
    if not st.session_state.repo_info:
        return

    info = st.session_state.repo_info
    artifacts = info.artifacts

    st.markdown("---")
    st.header("Step 5: Repository File Inventory View")
    st.markdown("Inspect every discovered file, its classification, extracted symbols, and relationship count.")

    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Status Filter", ["All Discovered Files", "RELEVANT Files Only", "IGNORED Files Only"])
    with col2:
        categories = sorted(list({getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')) for a in artifacts}))
        cat_filter = st.selectbox("Category Filter", ["All Categories"] + categories)

    filtered_artifacts = artifacts
    if status_filter == "RELEVANT Files Only":
        filtered_artifacts = [a for a in filtered_artifacts if getattr(a, 'status', 'RELEVANT') == "RELEVANT"]
    elif status_filter == "IGNORED Files Only":
        filtered_artifacts = [a for a in filtered_artifacts if getattr(a, 'status', 'RELEVANT') == "IGNORED"]

    if cat_filter != "All Categories":
        filtered_artifacts = [a for a in filtered_artifacts if getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')) == cat_filter]

    # Build DataFrame
    data = []
    for a in filtered_artifacts[:200]:  # Paginate top 200 for smooth UI rendering
        data.append({
            "Path": a.path,
            "Category": getattr(a, 'artifact_category', getattr(a, 'artifact_type', 'other')),
            "Type": getattr(a, 'file_type', getattr(a, 'artifact_type', 'other')),
            "Language": getattr(a, 'language', "-") or "-",
            "Lines": getattr(a, 'line_count', "-") if getattr(a, 'status', 'RELEVANT') == "RELEVANT" else "-",
            "Size (KB)": round(getattr(a, 'file_size', getattr(a, 'size_bytes', 0)) / 1024, 1),
            "Status": getattr(a, 'status', 'RELEVANT'),
            "Relationships": getattr(a, 'relationships_count', 0),
            "Ignore Reason": getattr(a, 'ignore_reason', "-") or "-",
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    if len(filtered_artifacts) > 200:
        st.caption(f"Showing first 200 of {len(filtered_artifacts)} matching artifacts.")

    # File Inspector
    selected_path = st.selectbox("Select an artifact to inspect facts and relationships:", [a.path for a in filtered_artifacts[:100]])
    if selected_path:
        selected_art = next((a for a in filtered_artifacts if a.path == selected_path), None)
        if selected_art:
            with st.expander(f"🔍 Inspector: `{selected_art.path}`", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Category:** `{getattr(selected_art, 'artifact_category', getattr(selected_art, 'artifact_type', 'other'))}`")
                c2.markdown(f"**Status:** `{getattr(selected_art, 'status', 'RELEVANT')}`")
                c3.markdown(f"**Lines:** `{getattr(selected_art, 'line_count', '-')}`")

                info_obj = getattr(selected_art, 'extracted_info', None)
                if info_obj:
                    st.markdown("#### Extracted Symbols & Facts")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if info_obj.functions:
                            st.markdown(f"**Functions ({len(info_obj.functions)}):**")
                            st.code("\n".join(f.value for f in info_obj.functions[:10]))
                        if info_obj.classes:
                            st.markdown(f"**Classes/Structs ({len(info_obj.classes)}):**")
                            st.code("\n".join(c.value for c in info_obj.classes[:10]))
                        if info_obj.dependencies:
                            st.markdown(f"**Dependencies ({len(info_obj.dependencies)}):**")
                            st.code("\n".join(d.value for d in info_obj.dependencies[:10]))
                    with col_b:
                        if info_obj.imports:
                            st.markdown(f"**Imports ({len(info_obj.imports)}):**")
                            st.code("\n".join(imp.value for imp in info_obj.imports[:10]))
                        if info_obj.api_routes:
                            st.markdown(f"**API Routes ({len(info_obj.api_routes)}):**")
                            st.code("\n".join(r.value for r in info_obj.api_routes[:10]))
                        if info_obj.config_keys:
                            st.markdown(f"**Config / Env Keys ({len(info_obj.config_keys)}):**")
                            st.code("\n".join(k.value for k in info_obj.config_keys[:10]))

def main():
    init_session_state()
    render_header()

    if not st.session_state.ingested_repo:
        # No repository loaded at all — show ingestion UI
        handle_ingestion()
    elif not st.session_state.repo_info:
        # Repository was ingested but repo_info is missing (evicted stale object or scan
        # hasn't run yet). Offer to rescan without re-entering the URL.
        repo = st.session_state.ingested_repo
        st.header("Step 2: Repository Scan Required")
        st.warning(
            "The cached repository analysis is outdated and was automatically discarded. "
            "Click the button below to rescan the already-loaded repository."
        )
        st.markdown(f"**Repository:** `{repo.original_source}`")
        if st.button("🔄 Rescan Repository", type="primary"):
            with st.spinner("Rescanning repository..."):
                _process_ingested_repo(repo)
        if st.button("✖ Load a Different Repository", type="secondary"):
            repo.cleanup()
            st.session_state.ingested_repo = None
            st.rerun()
    else:
        render_repository_overview()
        if not st.session_state.analysis_running and not st.session_state.reports:
            render_analysis_configuration()
        render_reports()
        render_file_analysis_view()

if __name__ == "__main__":
    main()
