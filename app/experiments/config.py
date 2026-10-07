import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

@dataclass
class ExperimentConfig:
    """Configuration for a single DriftGuard experiment run."""
    experiment_id: str
    repository: str
    commit: Optional[str] = None
    
    # Model Configuration
    model: str = "qwen2.5-coder:7b"
    prompt_version: str = "baseline_v1"
    
    # RAG Configuration
    rag_mode: str = "Non-RAG"  # Non-RAG, RAG, Hybrid
    chunking_strategy: str = "AST-aware"
    chunk_size: int = 512
    overlap: int = 64
    embedding_model: str = "all-MiniLM-L6-v2"
    retrieval_strategy: str = "Dense Embedding"
    top_k: int = 5
    
    # Dataset Configuration
    dataset_split: str = "Test"
    max_cases: int = 0  # 0 means all cases in the split
    
    # Flags
    enable_evidence_verification: bool = True
    enable_fix_validation: bool = False
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentConfig":
        data = json.loads(json_str)
        return cls(**data)

@dataclass
class ExperimentResult:
    """Results of a completed experiment."""
    experiment_id: str
    config: ExperimentConfig
    
    # Aggregate Metrics
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    macro_f1: Optional[float] = None
    false_positive_rate: Optional[float] = None
    
    evidence_accuracy: Optional[float] = None
    evidence_completeness: Optional[float] = None

    
    avg_latency_s: float = 0.0
    total_tokens: int = 0
    total_cases_analyzed: int = 0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_json(self) -> str:
        d = asdict(self)
        d["config"] = asdict(self.config)
        return json.dumps(d, indent=2)
