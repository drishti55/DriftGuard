#!/usr/bin/env python3
"""
Targeted diagnostic for pyproject.toml dependency extraction bug.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ingestion.artifact_extractor import extract_dependency_info

PYPROJECT_PATH = "/Users/drishti/Desktop/Projects/BUGTRACE prj/driftguard-dataset/repositories/fastapi_sqlmodel/pyproject.toml"

with open(PYPROJECT_PATH, 'r') as f:
    content = f.read()

print("=== pyproject.toml content (first 120 lines) ===")
for i, line in enumerate(content.split('\n')[:120], 1):
    print(f"{i:4d}: {line}")

print()
print("=== Extraction result ===")
info = extract_dependency_info(content, 'pyproject.toml')
print(f"Dependencies found: {len(info.dependencies)}")
for d in info.dependencies:
    print(f"  line {d.line_num}: {d.value!r}")
