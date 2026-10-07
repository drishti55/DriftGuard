# DriftGuard — Autonomous AIDevOps Consistency & Drift Platform

DriftGuard is an autonomous, open-source multi-agent code intelligence and consistency platform. It detects and audits subtle inconsistencies ("drift") between related software artifacts—such as source code, unit tests, dependency manifests, configuration files, and documentation—using multi-language AST perception, cross-file SCIP symbol graphs, and mathematically grounded LLM reasoning.

---

## 🏛️ Architecture Overview

```text
Git Working Tree / Delta
       ↓
Incremental Perception Agent (GitDeltaScanner)
       ↓
Technology Stack Detection (StackDetector)
       ↓
Multi-Language Code Intelligence (TreeSitterEngine: AST + SCIPIndexer)
       ↓
Candidate Pair Generation (Code ↔ Tests, Symbols ↔ Consumers, Code ↔ Manifests)
       ↓
Grounded Drift Auditor (DriftAuditorAgent via OmniRoute Gateway)
       ↓
Mathematical Verbatim Invariant Verification (EvidenceVerifier)
       ↓
Sandboxed Repair Engineer (Docker/local fallback + Kubernetes Job manifests)
       ↓
Compiler Reflection Loop (bounded by .driftguard.yml)
       ↓
CLI & Multi-Page Dashboard & FastAPI Server
```

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.12+ managed via [`uv`](https://docs.astral.sh/uv/)
- OmniRoute gateway running locally on `http://localhost:20128` (or local Ollama fallback)

### Installation
```bash
# Clone and navigate into workspace
git clone https://github.com/ojhaprathmesh/DriftGuard_Repo.git
cd DriftGuard_Repo

# Sync dependencies and lockfile
uv sync

# Configure environment
cp .env.example .env
```

### Running Tests
```bash
uv run pytest
uvx ruff check --select F401,F841 app/ tests/
```

---

## 🔧 Sandboxed Repair

Phase 3 verifies proposed fixes without modifying the host workspace. A temporary
copy receives the unified diff, then configured build and test commands run with
bounded timeouts. Docker is used when available; local isolated execution is the
safe fallback when Docker is unavailable. Kubernetes support generates a
non-root `batch/v1` Job manifest for cloud CI.

```bash
# Audit the current delta, generate a patch, and verify it in a sandbox
uv run driftguard repair --workspace . --max 3 --json
```

Repairs stop after `repair.max_attempts` from `.driftguard.yml`. Phase 3 does not
commit changes, push branches, or open pull requests.

---

## 💻 CLI Usage

DriftGuard provides a unified command-line tool accessible via `uv run driftguard` or `uv run python app/main.py`:

```bash
# 1. Autonomous consistency audit on git delta
uv run driftguard audit --max 5

# 2. Inspect git delta and modified hunks
uv run driftguard diff --base main

# 3. Detect technology stack and effective build matrix
uv run driftguard scan-stack

# 4. Ingest and run full perception
uv run driftguard perceive --base HEAD~1

# 5. Validate repository configuration
uv run driftguard config --show

# 6. Generate and verify a bounded sandboxed repair
uv run driftguard repair --max 3 --json

# 7. Launch the Streamlit multi-page management dashboard
uv run driftguard ui
```

---

## 📁 Repository Structure

```text
DriftGuard_Repo/
├── app/                         # Core Python platform
│   ├── agents/                  # Autonomous perception & audit agents
│   │   ├── coordinator.py       # Root coordinator agent
│   │   ├── delta_scanner.py     # Git diff & hunk perception
│   │   ├── stack_detector.py    # Polyglot stack & build matrix detection
│   │   ├── drift_auditor.py     # Grounded drift auditor agent
│   │   ├── repair_engineer.py   # Sandboxed unified-diff repair agent
│   │   └── reflection_agent.py  # Compiler/test feedback and bounded retries
│   ├── analysis/                # Drift detection & evidence validation
│   │   ├── drift_detector.py    # Baseline LLM drift detector
│   │   ├── drift_pipeline.py    # End-to-end analysis pipeline
│   │   ├── evidence_verifier.py # Verbatim substring citation verifier
│   │   ├── output_validator.py  # Structured JSON schema validation
│   │   ├── prompts.py           # Grounded prompt templates & few-shot specs
│   │   └── relationship_graph.py# Cross-artifact dependency graph
│   ├── api/                     # REST API layer
│   │   └── main.py              # FastAPI server & endpoints (/api/audit, etc.)
│   ├── cli.py                   # Unified CLI implementation
│   ├── main.py                  # CLI runner & package delegation wrapper
│   ├── config.py                # Environment & runtime configuration
│   ├── config_schema.py         # .driftguard.yml Pydantic schema
│   ├── ingestion/               # Repository loading & classification
│   │   ├── models.py            # RepoArtifact & RepoInfo canonical data models
│   │   ├── repository_loader.py # Workspace repository loader
│   │   ├── repository_scanner.py# Workspace scanner & classifier
│   │   ├── repository_ingestor.py # Git & archive workspace ingestion
│   │   ├── artifact_extractor.py# Structural regex extractor
│   │   └── file_classifier.py   # Multi-language file classification
│   ├── sandbox/                  # Isolated local/Docker execution and K8s manifests
│   │   ├── base.py               # Sandbox runner contract and execution result
│   │   ├── docker_runner.py      # Docker runner with local fallback
│   │   └── k8s_runner.py         # Kubernetes Job manifest generator
│   ├── intelligence/            # Multi-language code intelligence
│   │   ├── treesitter_parser.py # Universal AST engine (Python ast + TS/JS/Go Tree-sitter)
│   │   └── scip_indexer.py      # Cross-file SCIP symbol definition & reference graph
│   ├── retrieval/               # Vector retrieval & embeddings
│   │   ├── chunking.py          # Code chunking
│   │   ├── embeddings.py        # Sentence transformers
│   │   ├── vector_store.py      # ChromaDB interface
│   │   └── retriever.py         # Cross-artifact retriever
│   └── ui/                      # Streamlit management dashboard
│       ├── dashboard.py         # Multi-page dashboard navigation
│       ├── streamlit_app.py     # Consolidated single-page interactive UI
│       ├── session.py           # UI session state persistence
│       └── pages/               # Multi-page dashboard views
│           ├── 1_Overview.py
│           ├── 2_Drift_Explorer.py
│           ├── 3_Dependency_Graph.py
│           └── 4_Settings.py
│
├── frontend/                    # Vite + React + TypeScript web application
│   ├── src/                     # React application source
│   │   ├── components/AppShell.tsx
│   │   ├── pages/LandingPage.tsx
│   │   └── pages/AnalyzeMode.tsx
│   └── package.json
│
├── tests/                       # Automated test suite
│   ├── test_api.py              # FastAPI endpoints tests
│   ├── test_code_intelligence.py# Tree-sitter & SCIP indexer tests
│   ├── test_drift_auditor.py    # DriftAuditorAgent & verbatim invariant tests
│   ├── test_sandbox.py          # Isolated execution, patching, timeout, cleanup
│   ├── test_repair_reflection.py # Utility scoring and bounded retry tests
│   └── test_perception_and_config.py # Stack detection, delta scanner & config tests
│
├── pyproject.toml               # Modern PEP 621 dependencies & scripts
├── uv.lock                      # Deterministic lockfile
└── .driftguard.yml              # Workspace build & audit configuration
```

---

## 🛡️ Mathematical Grounding Invariant

To guarantee **zero hallucinations**, every candidate drift reported by DriftGuard must satisfy the strict verbatim citation property:

$$\text{Verdict} = \text{Confirmed Drift} \iff (F_1 \sqsubseteq C_1) \land (F_2 \sqsubseteq C_2)$$

Where:
- $F_1, F_2$ are the exact verbatim textual quotes extracted from Artifact 1 and Artifact 2.
- $C_1, C_2$ are the normalized file contents from disk.
- $\sqsubseteq$ denotes strict continuous substring inclusion.

Any finding where the LLM invents, paraphrases, or hallucinates line content is immediately discarded by `EvidenceVerifier`.
