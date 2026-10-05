"""
DriftGuard Retriever
Cross-artifact retrieval: given one artifact, find related artifacts in the same repo.
Builds context for RAG-enhanced drift detection.
"""

import logging
from typing import Optional

from app import config
from app.retrieval.vector_store import VectorStore
from app.ingestion.repository_loader import RepositoryLoader

logger = logging.getLogger(__name__)


class Retriever:
    """
    Retrieves related artifacts for RAG-enhanced drift detection.

    Given two artifacts under analysis, retrieves additional context
    from the same repository that may help the LLM make a better judgment.
    """

    def __init__(self, vector_store: VectorStore = None,
                 repo_loader: RepositoryLoader = None):
        self.vector_store = vector_store or VectorStore()
        self.repo_loader = repo_loader or RepositoryLoader()

    def retrieve_context(self, repository: str,
                         artifact_1_path: str, artifact_1_type: str,
                         artifact_2_path: str, artifact_2_type: str,
                         top_k: int = None) -> str:
        """
        Retrieve related repository context for a drift analysis.

        Strategy:
        1. Use artifact paths as queries to find related files
        2. Focus on artifact types that bridge the two being analyzed
        3. Return formatted context string for the LLM prompt

        Args:
            repository: Repo name (e.g., 'tiangolo/fastapi')
            artifact_1_path: Path of first artifact
            artifact_1_type: Type of first artifact
            artifact_2_path: Path of second artifact
            artifact_2_type: Type of second artifact
            top_k: Number of related artifacts to retrieve

        Returns:
            Formatted context string
        """
        top_k = top_k or config.TOP_K_RETRIEVAL
        context_parts = []

        # Exclude the two artifacts being analyzed
        exclude = [artifact_1_path, artifact_2_path]

        # Strategy 1: Search for artifacts related to artifact_1
        a1_query = f"{artifact_1_type} {artifact_1_path}"
        results_1 = self.vector_store.search(
            query_text=a1_query,
            repository=repository,
            n_results=top_k,
            exclude_paths=exclude,
        )

        # Strategy 2: Search for artifacts related to artifact_2
        a2_query = f"{artifact_2_type} {artifact_2_path}"
        results_2 = self.vector_store.search(
            query_text=a2_query,
            repository=repository,
            n_results=top_k,
            exclude_paths=exclude,
        )

        # Strategy 3: Search for bridging artifacts based on drift type
        bridge_type = _get_bridge_type(artifact_1_type, artifact_2_type)
        results_bridge = []
        if bridge_type:
            results_bridge = self.vector_store.search(
                query_text=f"{bridge_type} configuration",
                repository=repository,
                artifact_type=bridge_type,
                n_results=3,
                exclude_paths=exclude,
            )

        # Deduplicate and merge results
        seen_paths = set()
        all_results = []
        for r in results_1 + results_2 + results_bridge:
            path = r["metadata"].get("source_path", "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                all_results.append(r)

        # Limit total context
        all_results = all_results[:top_k + 2]

        # Format context
        for r in all_results:
            meta = r["metadata"]
            path = meta.get("source_path", "unknown")
            atype = meta.get("artifact_type", "unknown")
            text = r["text"][:1000]  # Limit per-chunk context
            context_parts.append(
                f"File: {path} (type: {atype})\n```\n{text}\n```"
            )

        if not context_parts:
            return "No additional repository context available."

        return "\n\n".join(context_parts)

    def build_index_for_repo(self, repository: str,
                             use_metadata: bool = True):
        """
        Build the vector index for a specific repository.

        Args:
            repository: Repo name
            use_metadata: Whether to use pre-extracted metadata or scan disk
        """
        from app.retrieval.chunking import chunk_artifact

        logger.info(f"Building index for {repository}...")

        # Load artifacts
        artifacts = self.repo_loader.load_repo_artifacts(repository, use_metadata=use_metadata)

        if not artifacts:
            logger.warning(f"No artifacts found for {repository}")
            return

        # Chunk and index each artifact
        all_chunks = []
        for artifact in artifacts:
            # For metadata-based loading, use content_snippet or read from disk
            content = artifact.content_snippet
            if not content and artifact.size_bytes < config.MAX_FILE_SIZE_BYTES:
                content = self.repo_loader.read_file_content(
                    repository, artifact.path, max_chars=config.MAX_CONTEXT_CHARS
                )

            if not content or content.startswith("["):
                continue

            chunks = chunk_artifact(
                content=content,
                filepath=artifact.path,
                repository=repository,
                artifact_type=artifact.artifact_type,
                max_chunk_size=config.CHUNK_SIZE,
                overlap=config.CHUNK_OVERLAP,
            )
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_store.add_chunks(all_chunks)
            logger.info(f"Indexed {len(all_chunks)} chunks for {repository}")
        else:
            logger.warning(f"No chunks generated for {repository}")


def _get_bridge_type(type_a: str, type_b: str) -> Optional[str]:
    """
    Determine what artifact type might 'bridge' the two being analyzed.
    For example, if analyzing dependency vs code, a build config might help.
    """
    pair = frozenset([type_a, type_b])

    bridges = {
        frozenset(["dependency", "source_code"]): "build_configuration",
        frozenset(["test", "source_code"]): "dependency",
        frozenset(["documentation", "source_code"]): "api_specification",
        frozenset(["ci_configuration", "source_code"]): "build_configuration",
        frozenset(["docker_configuration", "source_code"]): "dependency",
    }

    return bridges.get(pair)
