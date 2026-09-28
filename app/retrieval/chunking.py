"""
DriftGuard Chunking
Code-aware text chunking that respects function/class boundaries for source code
and section boundaries for documentation.
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single chunk of text with metadata."""
    text: str
    source_path: str
    artifact_type: str
    repository: str
    chunk_index: int = 0
    start_line: int = 0
    end_line: int = 0
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def chunk_source_code(content: str, filepath: str, repository: str,
                      artifact_type: str, max_chunk_size: int = 512,
                      overlap: int = 64) -> List[Chunk]:
    """
    Chunk source code respecting function/class boundaries where possible.

    Strategy:
    1. Try to split on function/class definitions
    2. If a function is too large, split on blank lines within it
    3. Fallback to character-based splitting with overlap
    """
    if not content.strip():
        return []

    lines = content.split('\n')
    chunks = []

    # Find function/class boundaries
    boundaries = []
    for i, line in enumerate(lines):
        # Python, JS/TS, Go, Rust, Java function/class starts
        if re.match(r'^\s{0,4}(class |def |async def |function |func |pub fn |fn |public |private |protected )', line):
            boundaries.append(i)
        # Also split on major section separators
        elif re.match(r'^#{1,3}\s', line):  # Markdown headers
            boundaries.append(i)

    if not boundaries:
        # No clear boundaries — use line-based chunking
        return _chunk_by_lines(lines, filepath, repository, artifact_type,
                               max_chunk_size, overlap)

    # Split into segments at boundaries
    segments = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(lines)
        segment_text = '\n'.join(lines[start:end])
        segments.append((start, end, segment_text))

    # Add any preamble (imports, etc.) before first boundary
    if boundaries[0] > 0:
        preamble = '\n'.join(lines[:boundaries[0]])
        if preamble.strip():
            segments.insert(0, (0, boundaries[0], preamble))

    # Merge small segments or split large ones
    chunk_idx = 0
    for start_line, end_line, segment in segments:
        if len(segment) <= max_chunk_size:
            chunks.append(Chunk(
                text=segment,
                source_path=filepath,
                artifact_type=artifact_type,
                repository=repository,
                chunk_index=chunk_idx,
                start_line=start_line,
                end_line=end_line,
            ))
            chunk_idx += 1
        else:
            # Split large segment
            sub_lines = segment.split('\n')
            sub_chunks = _chunk_by_lines(sub_lines, filepath, repository,
                                         artifact_type, max_chunk_size, overlap,
                                         start_offset=start_line)
            for sc in sub_chunks:
                sc.chunk_index = chunk_idx
                chunk_idx += 1
            chunks.extend(sub_chunks)

    return chunks


def chunk_documentation(content: str, filepath: str, repository: str,
                        max_chunk_size: int = 512, overlap: int = 64) -> List[Chunk]:
    """
    Chunk documentation by section headers.
    """
    if not content.strip():
        return []

    # Split on markdown headers
    sections = re.split(r'(?=^#{1,3}\s)', content, flags=re.MULTILINE)
    chunks = []
    chunk_idx = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chunk_size:
            chunks.append(Chunk(
                text=section,
                source_path=filepath,
                artifact_type="documentation",
                repository=repository,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1
        else:
            # Split large section by paragraphs
            paragraphs = section.split('\n\n')
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + 2 <= max_chunk_size:
                    current = current + "\n\n" + para if current else para
                else:
                    if current:
                        chunks.append(Chunk(
                            text=current,
                            source_path=filepath,
                            artifact_type="documentation",
                            repository=repository,
                            chunk_index=chunk_idx,
                        ))
                        chunk_idx += 1
                    current = para
            if current:
                chunks.append(Chunk(
                    text=current,
                    source_path=filepath,
                    artifact_type="documentation",
                    repository=repository,
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1

    return chunks


def chunk_config_file(content: str, filepath: str, repository: str,
                      artifact_type: str, max_chunk_size: int = 512) -> List[Chunk]:
    """
    Chunk configuration files (YAML, JSON, TOML, etc.).
    These are usually small enough to fit in one chunk.
    """
    if not content.strip():
        return []

    if len(content) <= max_chunk_size:
        return [Chunk(
            text=content,
            source_path=filepath,
            artifact_type=artifact_type,
            repository=repository,
            chunk_index=0,
        )]

    # For larger configs, split on top-level blocks
    lines = content.split('\n')
    return _chunk_by_lines(lines, filepath, repository, artifact_type, max_chunk_size, 32)


def chunk_artifact(content: str, filepath: str, repository: str,
                   artifact_type: str, max_chunk_size: int = 512,
                   overlap: int = 64) -> List[Chunk]:
    """
    Main entry point: chunk any artifact based on its type.
    """
    if artifact_type == "documentation":
        return chunk_documentation(content, filepath, repository, max_chunk_size, overlap)
    elif artifact_type == "source_code" or artifact_type == "test":
        return chunk_source_code(content, filepath, repository, artifact_type,
                                 max_chunk_size, overlap)
    else:
        return chunk_config_file(content, filepath, repository, artifact_type,
                                 max_chunk_size)


def _chunk_by_lines(lines: list, filepath: str, repository: str,
                    artifact_type: str, max_chunk_size: int,
                    overlap: int, start_offset: int = 0) -> List[Chunk]:
    """Fallback line-based chunking with overlap."""
    chunks = []
    current = ""
    current_start = start_offset
    chunk_idx = 0

    for i, line in enumerate(lines):
        if len(current) + len(line) + 1 > max_chunk_size and current:
            chunks.append(Chunk(
                text=current,
                source_path=filepath,
                artifact_type=artifact_type,
                repository=repository,
                chunk_index=chunk_idx,
                start_line=current_start,
                end_line=start_offset + i - 1,
            ))
            chunk_idx += 1

            # Overlap: keep last few lines
            overlap_lines = current.split('\n')[-3:]
            current = '\n'.join(overlap_lines) + '\n' + line
            current_start = start_offset + i - len(overlap_lines)
        else:
            current = current + '\n' + line if current else line

    if current.strip():
        chunks.append(Chunk(
            text=current,
            source_path=filepath,
            artifact_type=artifact_type,
            repository=repository,
            chunk_index=chunk_idx,
            start_line=current_start,
            end_line=start_offset + len(lines) - 1,
        ))

    return chunks
