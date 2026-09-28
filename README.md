# DriftGuard — AI-Powered Cross-Artifact Consistency Analyzer

DriftGuard detects inconsistencies ("drift") between related artifacts in software repositories using a local LLM + RAG pipeline. It analyzes whether code, tests, documentation, dependency files, CI configs, Dockerfiles, and API specs are in sync with each other.

## Architecture

```
Repository (local)
       ↓
Artifact Extraction & Classification
       ↓
Chunking → Embeddings → ChromaDB (Vector Index)
       ↓
Related Artifact Retrieval (RAG)
       ↓
LLM Analysis (Ollama — qwen2.5-coder:7b)
       ↓
Structured Drift Report (JSON)
       ↓
Streamlit UI / CLI / Export
```

## Dataset

The system is built on a curated dataset of **154,241 labelled consistency cases** from **489 open-source repositories** across 20 programming languages.

| Split | Cases | Purpose |
|-------|-------|---------|
| Train | 100,825 | Few-shot examples for prompts |
| Validation | 29,267 | Tuning and development |
| Test | 24,149 | Final evaluation benchmark |

Cases are split by **repository** (not randomly) to prevent data leakage.

### Drift Categories

| Category | Description |
|----------|-------------|
| `dependency_vs_code` | Module imported but not in dependency file |
| `test_vs_code` | Test references outdated code |
| `documentation_vs_code` | README/docs disagree with implementation |
| `api_spec_vs_code` | OpenAPI spec doesn't match API code |
| `ci_vs_project` | CI workflow is inconsistent with project |
| `docker_vs_project` | Dockerfile mismatches project structure |
| `build_config_vs_project` | Build config doesn't match code |
| `configuration_vs_code` | Config files disagree with source |
| `no_drift` | Artifacts are consistent (negative class) |

## Installation

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running
- At least one code model pulled:

```bash
ollama pull qwen2.5-coder:7b    # Primary (recommended)
ollama pull codellama:7b          # Fallback
```

### Setup

```bash
cd "BUGTRACE prj"

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Verify setup
python scripts/smoke_test.py
```

## Usage

### CLI — Analyze a Repository

```bash
# List available repositories
python scripts/run_analysis.py --list

# Analyze a specific repo
python scripts/run_analysis.py tiangolo/fastapi --max-pairs 10

# Save results to JSON
python scripts/run_analysis.py gin-gonic/gin --output results.json
```

### CLI — Run Evaluation

```bash
# Baseline evaluation (200 test cases)
python scripts/run_evaluation.py --mode baseline --sample-size 200

# RAG evaluation
python scripts/run_evaluation.py --mode rag --sample-size 200

# Run both and compare
python scripts/run_evaluation.py --mode both --sample-size 200

# Compare previously saved results
python scripts/run_evaluation.py --mode compare
```

### Streamlit UI

```bash
streamlit run app/ui/streamlit_app.py
```

### Unified CLI

```bash
python app/main.py analyze tiangolo/fastapi
python app/main.py evaluate --mode baseline --sample-size 20
python app/main.py ui
python app/main.py list
```

## Project Structure

```
BUGTRACE prj/
├── driftguard-dataset/          # Pre-built dataset (untouched)
│   ├── repositories/            # 531 cloned repos (36 GB)
│   ├── snapshots/               # 1,593 point-in-time copies (78 GB)
│   ├── metadata/                # Artifact index, drifts, cases
│   ├── splits/                  # train/val/test JSONL
│   └── scripts/                 # Dataset engineering pipeline
│
├── app/                         # AI application
│   ├── config.py                # Central configuration
│   ├── main.py                  # Unified CLI entry point
│   ├── analysis/                # LLM-powered drift detection
│   │   ├── llm_client.py        # Ollama wrapper with retry
│   │   ├── prompts.py           # Prompt templates + few-shot
│   │   ├── drift_detector.py    # Main orchestrator
│   │   └── output_validator.py  # Pydantic validation + JSON extraction
│   ├── ingestion/               # Repository loading
│   │   ├── repository_loader.py # Load from local dataset
│   │   ├── artifact_extractor.py# Code structure extraction
│   │   └── file_classifier.py   # File type classification
│   ├── retrieval/               # RAG pipeline
│   │   ├── chunking.py          # Code-aware chunking
│   │   ├── embeddings.py        # Sentence-transformers
│   │   ├── vector_store.py      # ChromaDB
│   │   └── retriever.py         # Cross-artifact retrieval
│   ├── evaluation/              # Benchmarking
│   │   ├── metrics.py           # F1, precision, recall, etc.
│   │   ├── evaluate_baseline.py # Direct LLM evaluation
│   │   ├── evaluate_rag.py      # RAG-enhanced evaluation
│   │   └── error_analysis.py    # Error breakdown + comparison
│   ├── validation/
│   │   └── fix_validator.py     # Suggested-fix validation
│   └── ui/
│       └── streamlit_app.py     # Web interface
│
├── scripts/                     # CLI entry points
│   ├── run_analysis.py          # Analyze a repository
│   ├── run_evaluation.py        # Run evaluations
│   └── smoke_test.py            # Verify pipeline
│
├── results/                     # Evaluation outputs
│   ├── predictions/             # Per-case predictions (JSONL)
│   ├── metrics/                 # Metric JSONs
│   └── reports/                 # Markdown reports
│
├── requirements.txt
├── .env.example
└── README.md
```

## Model Setup

DriftGuard uses **local LLM inference** via Ollama. No API keys or cloud services required.

| Model | Size | Role |
|-------|------|------|
| `qwen2.5-coder:7b` | 4.7 GB | Primary — best code understanding |
| `codellama:7b` | 3.8 GB | Fallback |
| `starcoder2:3b` | 1.7 GB | Fast/lightweight option |
| `gemma2:9b` | 5.4 GB | General reasoning |

## Evaluation Metrics

### Drift Detection (Binary)
- Accuracy, Precision, Recall, F1-Score
- False Positive Rate, False Negative Rate

### Drift Classification (Multi-class)
- Classification Accuracy, Macro-F1
- Per-category Precision, Recall, F1
- Confusion Matrix

### Severity Prediction
- Accuracy, Macro-F1

### Evidence Quality (Heuristic)
- Artifact mention rate
- Substantiveness rate
- Identifier mention rate

## Limitations

- **Test set imbalance:** 89.4% of test cases are `dependency_vs_code` — evaluation uses stratified sampling and per-class metrics to mitigate
- **LLM speed:** A 7B model processes ~1-3 cases/min locally; full test set (24k) requires overnight runs
- **Heuristic evidence quality:** Evidence evaluation is rule-based, not human-judged
- **Natural drift detection is heuristic-based:** Some detected drifts in the dataset may be false positives
- **No fine-tuning performed:** The model is used zero/few-shot; fine-tuning could improve accuracy
- **Fix validation is basic:** Only checks syntax, not semantic correctness

## Future Work

- Fine-tune a code model on the 100k training cases
- Add GitHub PR webhook integration
- Human evaluation of evidence and fix quality
- Support for more languages (Haskell, Elixir, etc.)
- IDE extension (VS Code / JetBrains)
- Confidence calibration
