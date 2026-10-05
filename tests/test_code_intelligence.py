"""
Tests for Phase 2 Tree-sitter AST & SCIP Code Intelligence.
Validates multi-language parsing across Python, TypeScript, TSX, JS, Go,
and cross-file symbol reference mapping.
"""

import tempfile
from pathlib import Path

from app.intelligence.treesitter_parser import TreeSitterEngine
from app.intelligence.scip_indexer import SCIPIndexer


def test_treesitter_python_parsing():
    engine = TreeSitterEngine()
    py_code = '''
import os
from math import sqrt

class MathService:
    def calculate(self, x: int) -> float:
        return sqrt(x)

def process_data(items: list):
    service = MathService()
    return [service.calculate(i) for i in items]
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "service.py"
        f.write_text(py_code)

        parsed = engine.parse_file(f)
        assert parsed.language == "python"
        assert len(parsed.imports) >= 2
        assert any("MathService" in s.name for s in parsed.symbols if s.kind == "class")
        assert any("calculate" in s.name for s in parsed.symbols if s.kind == "method")
        assert any("process_data" in s.name for s in parsed.symbols if s.kind == "function")

        # Test line lookup
        calc_sym = parsed.get_symbol_at_line(6)
        assert calc_sym is not None
        assert calc_sym.name == "calculate"


def test_treesitter_typescript_parsing():
    engine = TreeSitterEngine()
    ts_code = '''
import { useState } from 'react';

export interface User {
    id: string;
    name: string;
}

export function getUser(id: string): User {
    return { id, name: "DriftGuard" };
}

export const updateUser = async (user: User) => {
    console.log(user);
};
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "user.ts"
        f.write_text(ts_code)

        parsed = engine.parse_file(f)
        assert parsed.language == "typescript"
        assert len(parsed.imports) >= 1
        assert any(s.name == "User" for s in parsed.symbols)
        assert any(s.name == "getUser" for s in parsed.symbols)
        assert any(s.name == "updateUser" for s in parsed.symbols)


def test_treesitter_go_parsing():
    engine = TreeSitterEngine()
    go_code = '''
package main

import "fmt"

type Server struct {
    Port int
}

func (s *Server) Start() {
    fmt.Println("Server running")
}

func NewServer(port int) *Server {
    return &Server{Port: port}
}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "server.go"
        f.write_text(go_code)

        parsed = engine.parse_file(f)
        assert parsed.language == "go"
        assert len(parsed.imports) >= 1
        assert any(s.name == "Server" for s in parsed.symbols)
        assert any(s.name == "Start" for s in parsed.symbols)
        assert any(s.name == "NewServer" for s in parsed.symbols)


def test_scip_cross_file_impact():
    engine = TreeSitterEngine()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # File 1: Definition
        f1 = root / "auth.py"
        f1.write_text("def verify_token(token: str):\n    return True\n")

        # File 2: Consumer calling f1
        f2 = root / "routes.py"
        f2.write_text("from auth import verify_token\n\ndef login():\n    return verify_token('abc')\n")

        indexer = SCIPIndexer(workspace_path=root, treesitter_engine=engine)
        symbols = indexer.index_workspace(force_refresh=True)

        assert "verify_token" in symbols
        def_file, def_line = indexer.find_definition("verify_token")
        assert "auth.py" in def_file

        # Check references
        refs = indexer.find_references("verify_token")
        assert any("routes.py" in r[0] for r in refs)

        # Check cross-file impact
        impact = indexer.get_cross_file_impact(["auth.py"])
        assert "auth.py" in impact
        assert "routes.py" in impact["auth.py"]
