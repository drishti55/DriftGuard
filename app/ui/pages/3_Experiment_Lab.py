import streamlit as st
import uuid
import time
from pathlib import Path
from app.experiments.config import ExperimentConfig
from app.experiments.runner import ExperimentRunner
from app.utils.repo_utils import normalize_repository_name

st.title("🧪 Experiment Lab")
st.markdown("Configure and run controlled drift detection experiments.")

if "runner" not in st.session_state:
    st.session_state.runner = ExperimentRunner(Path("results/experiments"))

col1, col2 = st.columns(2)

with col1:
    st.subheader("General Configuration")
    exp_id = st.text_input("Experiment ID", value=f"exp-{uuid.uuid4().hex[:6]}")
    repo_choice = st.selectbox("Repository", ["Loaded Workspace", "Dataset: All", "Dataset: Specific..."])
    
    repo_name = ""
    if repo_choice == "Loaded Workspace":
        if st.session_state.get("repo_info"):
            repo_name = st.session_state.repo_info.full_name
        else:
            st.warning("No workspace loaded.")
    elif repo_choice == "Dataset: Specific...":
        raw_repo = st.text_input("Dataset Repository Name", "tiangolo/fastapi")
        repo_name = normalize_repository_name(raw_repo)
    else:
        repo_name = "all"
        
    dataset_split = st.selectbox("Dataset Evaluation Split", ["Test", "Validation", "Train", "Runtime (Workspace)"])
    max_cases = st.number_input("Max Cases (0 = All)", 0, 5000, 100)

with col2:
    st.subheader("Model & Pipeline")
    model = st.selectbox("LLM Model", ["qwen2.5-coder:7b", "codellama:7b", "starcoder2:3b", "gemma2:9b"])
    
    rag_mode = st.radio("Analysis Mode", ["Non-RAG", "RAG", "Hybrid"])
    
    chunk_strategy = st.selectbox("Chunking Strategy", ["AST-aware", "Fixed Size", "Line Based", "Function Level"], disabled=(rag_mode=="Non-RAG"))
    retrieval_strategy = st.selectbox("Retrieval Strategy", ["Dense Embedding", "BM25 / Keyword", "Hybrid"], disabled=(rag_mode=="Non-RAG"))
    top_k = st.slider("Top-K Context", 1, 20, 5, disabled=(rag_mode=="Non-RAG"))
    
    verify_evidence = st.checkbox("Enable Evidence Verification", value=True)

st.markdown("---")

if st.button("🚀 RUN EXPERIMENT", type="primary", use_container_width=True):
    if repo_choice == "Loaded Workspace" and not st.session_state.get("repo_info"):
        st.error("Cannot run on Loaded Workspace without loading a repository first.")
        st.stop()
        
    config = ExperimentConfig(
        experiment_id=exp_id,
        repository=repo_name,
        model=model,
        rag_mode=rag_mode,
        chunking_strategy=chunk_strategy,
        retrieval_strategy=retrieval_strategy,
        top_k=top_k,
        dataset_split=dataset_split,
        max_cases=max_cases,
        enable_evidence_verification=verify_evidence
    )
    
    with st.spinner(f"Running experiment {exp_id}..."):
        from app.analysis.llm_client import LLMClient
        llm = LLMClient(model=model)
        if not llm.check_model_available(model):
            st.error(f"MODEL NOT AVAILABLE\n{model} is not installed in Ollama.")
            st.stop()
            
        # For workspace runtime, we use dynamic pairs
        cases_override = None
        if dataset_split == "Runtime (Workspace)":
            st.info("Using workspace cases (this will run analysis on the loaded repository).")
            cases_override = []
            if st.session_state.get("repo_info") and st.session_state.get("ingested_repo"):
                info = st.session_state.repo_info
                repo = st.session_state.ingested_repo
                
                from collections import defaultdict
                by_type = defaultdict(list)
                for a in info.artifacts:
                    by_type[a.artifact_type].append(a)

                pair_rules = [
                    ("dependency", "source_code"),
                    ("test", "source_code"),
                    ("documentation", "source_code"),
                    ("api_specification", "source_code"),
                    ("ci_configuration", "source_code"),
                    ("docker_configuration", "dependency"),
                    ("docker_configuration", "source_code"),
                    ("build_configuration", "source_code"),
                ]

                i = 0
                for type_a, type_b in pair_rules:
                    for a1 in by_type.get(type_a, []):
                        for a2 in by_type.get(type_b, []):
                            cases_override.append({
                                "case_id": f"runtime-{i}",
                                "repository": repo.original_source,
                                "commit_sha": info.commit_sha,
                                "artifact_1": {"path": a1.path, "type": a1.artifact_type},
                                "artifact_2": {"path": a2.path, "type": a2.artifact_type},
                            })
                            i += 1
            if not cases_override:
                st.warning("No related artifact pairs found to check in the workspace.")
                st.stop()
        
        progress_bar = st.progress(0)
        
        def progress_cb(current, total, report):
            progress_bar.progress(current / total if total > 0 else 1.0)
            
        result = st.session_state.runner.run(config, cases_override=cases_override, progress_callback=progress_cb)
        
        if result.f1_score is None:
            st.warning("EXPERIMENT COMPLETED WITH 0 EVALUATED CASES\nNo performance metrics were calculated. Check repository normalization or dataset coverage.")
        else:
            st.success(f"Experiment {exp_id} completed successfully!")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Macro F1", f"{result.macro_f1:.3f}")
            c2.metric("Precision", f"{result.precision:.3f}")
            c3.metric("Recall", f"{result.recall:.3f}")
            c4.metric("Avg Latency", f"{result.avg_latency_s:.1f}s")

