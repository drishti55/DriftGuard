from app.evaluation.drift_graph import DriftDependencyGraph

class PredictiveDrift:
    """Predicts potential drift based on PR diffs or changed files."""
    def __init__(self, graph: DriftDependencyGraph):
        self.graph = graph
        
    def predict_impact(self, changed_files: list) -> dict:
        """Returns artifacts potentially impacted by the changes."""
        impact = {}
        for file in changed_files:
            impact[file] = self.graph.get_affected_artifacts(file)
        return impact
