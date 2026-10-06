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
    temperature: float = 0.0
    max_tokens: int = 1024
    
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
    debug_sample_mode: bool = False
    
    # Flags
    enable_evidence_verification: bool = True
    enable_fix_validation: bool = False
    description: Optional[str] = None
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
        
    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentConfig":
        data = json.loads(json_str)
        return cls.from_dict(data)

@dataclass
class ExperimentResult:
    """Results of a completed experiment."""
    experiment_id: str
    config: ExperimentConfig
    
    # Aggregate Detection Metrics
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    macro_f1: Optional[float] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None
    confusion_matrix: Optional[Dict[str, int]] = None
    
    # Multi-dimensional breakdowns
    drift_type_metrics: Optional[Dict[str, Any]] = None
    repository_metrics: Optional[Dict[str, Any]] = None
    language_metrics: Optional[Dict[str, Any]] = None
    
    # Evidence Metrics
    evidence_accuracy: Optional[float] = None
    evidence_completeness: Optional[float] = None
    
    # Operational Metrics
    avg_latency_s: float = 0.0
    total_tokens: int = 0
    total_cases_analyzed: int = 0
    total_cases_in_dataset: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_unavailable: int = 0
    status: str = "COMPLETED"  # COMPLETED, IN_PROGRESS, FAILED, NOT RUN / MODEL UNAVAILABLE
    status_reason: Optional[str] = None
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_json(self) -> str:
        d = asdict(self)
        d["config"] = asdict(self.config)
        return json.dumps(d, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentResult":
        config_data = data.pop("config", {})
        if isinstance(config_data, dict):
            config = ExperimentConfig.from_dict(config_data)
        else:
            config = config_data
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(config=config, **filtered)
