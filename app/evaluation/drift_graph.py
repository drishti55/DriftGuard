class DriftDependencyGraph:
    """Constructs and manages the artifact dependency graph."""
    def __init__(self):
        self.nodes = {}
        self.edges = []
        
    def add_artifact(self, artifact_path: str, artifact_type: str):
        self.nodes[artifact_path] = artifact_type
        
    def add_dependency(self, source_path: str, target_path: str):
        self.edges.append((source_path, target_path))
        
    def get_affected_artifacts(self, changed_path: str) -> list:
        """Finds all artifacts that depend on the changed artifact."""
        affected = set()
        for src, target in self.edges:
            if target == changed_path:
                affected.add(src)
        return list(affected)
