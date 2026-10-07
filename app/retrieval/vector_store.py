"""
DriftGuard Vector Store
ChromaDB-based vector store for indexing and searching repository artifacts.
"""

import logging
from typing import List
from pathlib import Path

import chromadb
from chromadb.config import Settings

from app import config
from app.retrieval.embeddings import embed_texts

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB vector store for repository artifact embeddings.
    Stores chunks with metadata (repo, path, type) for filtered retrieval.
    """

    def __init__(self, persist_dir: str = None, collection_name: str = "driftguard_artifacts"):
        persist_dir = persist_dir or str(config.CHROMA_PERSIST_DIR)

        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = collection_name
        self._collection = None

    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(self, chunks, batch_size: int = 100):
        """
        Add chunks to the vector store with their embeddings.

        Args:
            chunks: List of Chunk objects (from chunking.py)
            batch_size: Number of chunks to embed and add at once
        """
        if not chunks:
            return

        total = len(chunks)
        logger.info(f"Adding {total} chunks to vector store...")

        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]

            texts = [c.text for c in batch]
            embeddings = embed_texts(texts)

            ids = [f"{c.repository}::{c.source_path}::chunk_{c.chunk_index}" for c in batch]
            metadatas = [{
                "repository": c.repository,
                "source_path": c.source_path,
                "artifact_type": c.artifact_type,
                "chunk_index": c.chunk_index,
                "start_line": c.start_line,
                "end_line": c.end_line,
            } for c in batch]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            if (i + batch_size) % 500 == 0 or i + batch_size >= total:
                logger.info(f"  Added {min(i + batch_size, total)}/{total} chunks")

    def search(self, query_text: str, repository: str = None,
               artifact_type: str = None, n_results: int = 5,
               exclude_paths: List[str] = None) -> List[dict]:
        """
        Search for similar chunks.

        Args:
            query_text: Text to search for
            repository: Filter by repository name
            artifact_type: Filter by artifact type
            n_results: Number of results to return
            exclude_paths: File paths to exclude from results

        Returns:
            List of dicts with 'text', 'metadata', and 'distance'
        """
        where_filter = {}
        if repository:
            where_filter["repository"] = repository
        if artifact_type:
            where_filter["artifact_type"] = artifact_type

        query_embedding = embed_texts([query_text])

        kwargs = {
            "query_embeddings": query_embedding,
            "n_results": n_results,
        }
        if where_filter:
            if len(where_filter) > 1:
                kwargs["where"] = {"$and": [
                    {k: {"$eq": v}} for k, v in where_filter.items()
                ]}
            else:
                kwargs["where"] = {k: {"$eq": v} for k, v in where_filter.items()}

        results = self.collection.query(**kwargs)

        # Format results
        formatted = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 0

                # Skip excluded paths
                if exclude_paths and meta.get("source_path") in exclude_paths:
                    continue

                formatted.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                })

        return formatted

    def get_collection_stats(self) -> dict:
        """Get stats about the current collection."""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
        }

    def reset(self):
        """Delete and recreate the collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None
        logger.info(f"Reset collection: {self.collection_name}")
