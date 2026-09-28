#!/usr/bin/env python3
"""
Pipeline diagnostic: Trace every stage from artifact discovery to candidate generation.
Run with: python diagnose_pipeline.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from collections import Counter

from app.ingestion.repository_ingestor import RepositoryIngestor, IngestedRepository
from app.ingestion.repository_scanner import RepositoryScanner
from app.ingestion.artifact_extractor import extract_info
from app.analysis.relationship_graph import RelationshipGraph

REPO_PATH = "/Users/drishti/Desktop/Projects/BUGTRACE prj/driftguard-dataset/repositories/fastapi_sqlmodel"

print("=" * 70)
print("DRIFTGUARD PIPELINE DIAGNOSTIC")
print("=" * 70)
print(f"Repository: {REPO_PATH}")
print()

# Stage 1: Ingest
print("── STAGE 1: INGESTION ──")
ingestor = RepositoryIngestor()
repo = ingestor.ingest_from_local(REPO_PATH)
print(f"  workspace_path : {repo.workspace_path}")
print(f"  source_type    : {repo.source_type}")
print(f"  commit_sha     : {repo.commit_sha}")
print()

# Stage 2: Scan
print("── STAGE 2: SCANNING ──")
scanner = RepositoryScanner()
info = scanner.scan(repo)
print(f"  scan_metrics   : {info.scan_metrics}")
print(f"  language       : {info.language}")
print(f"  framework      : {info.framework}")
print(f"  artifact_type_counts: {info.artifact_type_counts}")
print(f"  total artifacts: {len(info.artifacts)}")
print()

# Stage 3: Artifact Breakdown
print("── STAGE 3: ARTIFACT BREAKDOWN ──")
relevant = [a for a in info.artifacts if a.status == "RELEVANT"]
ignored  = [a for a in info.artifacts if a.status == "IGNORED"]
print(f"  RELEVANT: {len(relevant)}")
print(f"  IGNORED : {len(ignored)}")
print()

cat_counts = Counter(a.artifact_category for a in relevant)
print("  Category counts (RELEVANT artifacts):")
for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"    {cat:40s} : {count}")
print()

# Stage 4: Check artifact_category vs artifact_type
print("── STAGE 4: SCHEMA CHECK ──")
mismatches = [(a.path, a.artifact_type, a.artifact_category)
              for a in relevant if a.artifact_type != a.artifact_category]
print(f"  artifact_type != artifact_category mismatches: {len(mismatches)}")
for path, at, ac in mismatches[:5]:
    print(f"    path={path!r}  artifact_type={at!r}  artifact_category={ac!r}")
print()

# Stage 5: Fact extraction check
print("── STAGE 5: FACT EXTRACTION ──")
src = [a for a in relevant if a.artifact_category == "source_code"]
tst = [a for a in relevant if a.artifact_category == "test"]
dep = [a for a in relevant if a.artifact_category == "dependency"]
doc = [a for a in relevant if a.artifact_category == "documentation"]
ci  = [a for a in relevant if a.artifact_category == "ci_configuration"]
dkr = [a for a in relevant if a.artifact_category == "docker_configuration"]

print(f"  source_code artifacts : {len(src)}")
print(f"  test artifacts        : {len(tst)}")
print(f"  dependency artifacts  : {len(dep)}")
print(f"  documentation         : {len(doc)}")
print(f"  ci_configuration      : {len(ci)}")
print(f"  docker_configuration  : {len(dkr)}")
print()

src_with_facts   = [a for a in src if a.extracted_info is not None]
tst_with_facts   = [a for a in tst if a.extracted_info is not None]
dep_with_facts   = [a for a in dep if a.extracted_info is not None]
print(f"  source_code with extracted_info : {len(src_with_facts)} / {len(src)}")
print(f"  test        with extracted_info : {len(tst_with_facts)} / {len(tst)}")
print(f"  dependency  with extracted_info : {len(dep_with_facts)} / {len(dep)}")
print()

# Show sample imports
total_src_imports = sum(len(a.extracted_info.imports) for a in src_with_facts)
total_tst_imports = sum(len(a.extracted_info.imports) for a in tst_with_facts)
total_dep_pkgs    = sum(len(a.extracted_info.dependencies) for a in dep_with_facts)
print(f"  Total imports from source_code  : {total_src_imports}")
print(f"  Total imports from tests         : {total_tst_imports}")
print(f"  Total deps from dependency files : {total_dep_pkgs}")
print()

# Show stems
print("  Source file stems (first 10):")
for s in src[:10]:
    print(f"    {s.path}")
print()
print("  Test file stems (first 10):")
for t in tst[:10]:
    print(f"    {t.path}")
print()
print("  Dependency files:")
for d in dep[:10]:
    print(f"    {d.path}  ->  facts extracted: {d.extracted_info is not None}")
    if d.extracted_info:
        print(f"       deps: {[dd.value for dd in d.extracted_info.dependencies[:5]]}")
print()

# Stage 6: Relationship graph
print("── STAGE 6: RELATIONSHIP GRAPH ──")
workspace = repo.workspace_path
graph = RelationshipGraph(workspace_path=workspace)
edges = graph.build_graph(relevant)
print(f"  Edges built: {len(edges)}")
print()

if len(edges) == 0:
    print("  ⚠ NO EDGES — diagnosing root cause:")
    print()

    # Test relationship matching
    src_stems = {Path(s.path).stem.lower(): s for s in src}
    print(f"  Source stems (first 20): {list(src_stems.keys())[:20]}")
    print()
    print("  Test files and their candidate stem matches:")
    for t in tst[:20]:
        t_stem = Path(t.path).stem.lower()
        cands = [
            t_stem.replace("_test", ""),
            t_stem.replace(".test", ""),
            t_stem.replace(".spec", ""),
            t_stem.replace("test_", ""),
            t_stem.replace("test", ""),
        ]
        matched = [c for c in cands if c and c in src_stems]
        print(f"    {t.path:60s} -> stems={cands} -> matched={matched}")
    print()

    # Dependency matching
    print("  Dependency → Source matching:")
    for d in dep:
        if d.extracted_info:
            dep_names = {dd.value.split()[0].lower() for dd in d.extracted_info.dependencies}
            print(f"    {d.path}: {len(dep_names)} packages declared")
            print(f"      sample: {list(dep_names)[:10]}")
            for s in src_with_facts[:5]:
                imp_pkgs = {imp.value.split('/')[0].lower() for imp in s.extracted_info.imports}
                overlap = imp_pkgs & dep_names
                if overlap:
                    print(f"      {s.path} imports overlap: {overlap}")
else:
    edge_types = Counter(e.relationship_type for e in edges)
    print(f"  Edge types: {dict(edge_types)}")
    print(f"  Sample edges:")
    for e in edges[:10]:
        print(f"    [{e.relationship_type}] {e.artifact_1_path}  <->  {e.artifact_2_path}")
    print()

# Stage 7: Candidates
print("── STAGE 7: CANDIDATE GENERATION ──")
candidates = graph.generate_candidates()
print(f"  Candidates: {len(candidates)}")
if candidates:
    for c in candidates[:5]:
        print(f"    [{c['relationship_type']}] {c['artifact_1']['path']}  <->  {c['artifact_2']['path']}")
print()

print("── SUMMARY ──")
print(f"  Files discovered      : {info.scan_metrics.get('files_discovered')}")
print(f"  Relevant artifacts    : {info.scan_metrics.get('relevant_artifacts')}")
print(f"  Ignored vendor/cache  : {info.scan_metrics.get('ignored_vendor_cache')}")
print(f"  Relationships built   : {len(edges)}")
print(f"  Candidates generated  : {len(candidates)}")
print()

if len(candidates) == 0:
    print("  ❌ PIPELINE FAILURE: Zero candidates. The analysis cannot run.")
    print("     Root cause must be identified from the stages above.")
else:
    print("  ✅ Pipeline working. Analysis can proceed.")
