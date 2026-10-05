"""
DriftGuard Sourcegraph SCIP Open-Source Code Intelligence Integration.
Provides cross-file symbol definition and reference tracking.
Supports native local SCIP CLI indexers with deterministic Tree-sitter AST fallback.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.intelligence.treesitter_parser import TreeSitterEngine

logger = logging.getLogger(__name__)


@dataclass
class SCIPSymbolRef:
    """Represents a cross-file symbol definition and its reference sites."""
    name: str
    kind: str
    defined_in: str
    def_line: int
    signature: str = ""
    references: List[Tuple[str, int]] = field(default_factory=list)  # (file_path, line_number)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "defined_in": self.defined_in,
            "def_line": self.def_line,
            "signature": self.signature,
            "references_count": len(self.references),
            "references": [{"file": f, "line": l} for f, l in self.references],
        }


class SCIPIndexer:
    """
    Open-Source Code Intelligence Indexer.
    Attempts execution of local SCIP CLI indexers (scip-python, scip-typescript, scip-go)
    and falls back to universal in-process Tree-sitter symbol graph resolution.
    """

    def __init__(self, workspace_path: Path, treesitter_engine: Optional[TreeSitterEngine] = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.ts = treesitter_engine or TreeSitterEngine()
        self._symbols: Dict[str, SCIPSymbolRef] = {}
        self._indexed: bool = False

    def is_scip_cli_available(self, language: str) -> bool:
        """Checks if native open-source SCIP indexer binary exists in system PATH."""
        cli_map = {
            "python": "scip-python",
            "typescript": "scip-typescript",
            "javascript": "scip-typescript",
            "go": "scip-go",
        }
        cmd = cli_map.get(language)
        return bool(cmd and shutil.which(cmd))

    def index_workspace(self, force_refresh: bool = False) -> Dict[str, SCIPSymbolRef]:
        """
        Builds or retrieves the workspace cross-file symbol index.
        """
        if self._indexed and not force_refresh:
            return self._symbols

        self._symbols.clear()

        # Attempt native SCIP indexing if available
        for lang in ("python", "typescript", "go"):
            if self.is_scip_cli_available(lang):
                try:
                    self._run_scip_cli(lang)
                except Exception as e:
                    logger.debug(f"SCIP CLI failed for {lang}, using AST fallback: {e}")

        # In-process AST symbol graph (always active for complete coverage)
        self._build_ast_symbol_graph()

        self._indexed = True
        return self._symbols

    def _run_scip_cli(self, language: str):
        """Runs the native SCIP CLI indexer to generate index.scip."""
        cmd = ["scip-" + ("typescript" if language in ("typescript", "javascript") else language), "index"]
        logger.info(f"Running SCIP CLI indexer: {' '.join(cmd)}")
        subprocess.run(
            cmd,
            cwd=self.workspace_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60,
        )

    def _build_ast_symbol_graph(self):
        """
        Builds a cross-file symbol graph using universal Tree-sitter parsing:
        Phase 1: Discover all symbol definitions across files.
        Phase 2: Discover all symbol call sites / imports across files and connect reference edges.
        """
        # Discover files to parse
        source_files: List[Path] = []
        for p in self.workspace_path.rglob("*"):
            if p.is_file() and self.ts.supports_file(p):
                rel = str(p.relative_to(self.workspace_path))
                if any(part.startswith('.') for part in rel.split('/')):
                    continue
                if any(d in rel.split('/') for d in {'node_modules', 'vendor', '__pycache__', '.git', 'venv', '.venv'}):
                    continue
                source_files.append(p)

        parsed_files = {}
        # Phase 1: Index definitions
        for sf in source_files:
            rel = str(sf.relative_to(self.workspace_path))
            parsed = self.ts.parse_file(sf)
            parsed_files[rel] = parsed

            for sym in parsed.symbols:
                # Store symbol by name
                if sym.name not in self._symbols:
                    self._symbols[sym.name] = SCIPSymbolRef(
                        name=sym.name,
                        kind=sym.kind,
                        defined_in=rel,
                        def_line=sym.start_line,
                        signature=sym.signature,
                    )

        # Phase 2: Index cross-file references
        for rel, parsed in parsed_files.items():
            for call_name in parsed.calls:
                # Handle compound calls like 'module.function'
                base_name = call_name.split('.')[-1]
                if base_name in self._symbols:
                    ref_target = self._symbols[base_name]
                    if ref_target.defined_in != rel:
                        ref_target.references.append((rel, 0))

    def find_references(self, symbol_name: str) -> List[Tuple[str, int]]:
        """Returns all (file_path, line_number) references to the symbol."""
        if not self._indexed:
            self.index_workspace()
        ref = self._symbols.get(symbol_name)
        return ref.references if ref else []

    def find_definition(self, symbol_name: str) -> Optional[Tuple[str, int]]:
        """Returns (file_path, line_number) where symbol is defined."""
        if not self._indexed:
            self.index_workspace()
        ref = self._symbols.get(symbol_name)
        return (ref.defined_in, ref.def_line) if ref else None

    def get_cross_file_impact(self, changed_files: List[str]) -> Dict[str, Set[str]]:
        """
        Maps each changed file to other files in the workspace that reference its symbols.
        Used by DriftAuditorAgent to focus candidate generation on impacted consumers.
        """
        if not self._indexed:
            self.index_workspace()

        impact_map: Dict[str, Set[str]] = {f: set() for f in changed_files}
        changed_set = set(changed_files)

        for sym in self._symbols.values():
            if sym.defined_in in changed_set:
                for ref_file, _ in sym.references:
                    if ref_file not in changed_set:
                        impact_map[sym.defined_in].add(ref_file)

        return impact_map
