from typing import List, Dict
from app.experiments.config import ExperimentConfig
from app.experiments.runner import ExperimentRunner, ExperimentResult

class AblationStudy:
    """Manages running ablation experiments by systematically turning off components."""
    
    def __init__(self, runner: ExperimentRunner):
        self.runner = runner
        
    def run_ablation(self, base_config: ExperimentConfig) -> Dict[str, ExperimentResult]:
        """Runs the baseline config and versions with ablated components."""
        results = {}
        
        # 1. Full System
        results["Full System"] = self.runner.run(base_config)
        
        # 2. Without RAG
        no_rag_config = ExperimentConfig.from_json(base_config.to_json())
        no_rag_config.experiment_id += "-no-rag"
        no_rag_config.rag_mode = "Non-RAG"
        results["Without RAG"] = self.runner.run(no_rag_config)
        
        # 3. Without Evidence Verification
        no_ev_config = ExperimentConfig.from_json(base_config.to_json())
        no_ev_config.experiment_id += "-no-evidence"
        no_ev_config.enable_evidence_verification = False
        results["Without Evidence Verification"] = self.runner.run(no_ev_config)
        
        return results
