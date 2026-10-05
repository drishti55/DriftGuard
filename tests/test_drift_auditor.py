"""
Tests for Phase 2 Drift Auditor Agent.
Validates candidate generation, verbatim anti-hallucination invariant,
and integration with the Coordinator Agent blackboard state.
"""

import tempfile
from pathlib import Path

from app.agents.coordinator import CoordinatorAgent
from app.agents.delta_scanner import ChangedFile, GitDeltaReport
from app.agents.drift_auditor import DriftAuditorAgent
from app.analysis.output_validator import DriftPrediction


def test_candidate_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".driftguard.yml").write_text("version: '1.0'\n")

        # Create source file and corresponding test
        f_src = root / "math_ops.py"
        f_src.write_text("def add(a, b):\n    return a + b\n")

        f_test = root / "test_math_ops.py"
        f_test.write_text("from math_ops import add\ndef test_add():\n    assert add(1, 2) == 3\n")

        # Create pyproject.toml
        (root / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        auditor = DriftAuditorAgent(workspace_path=root)
        fake_delta = GitDeltaReport(
            workspace_path=str(root),
            current_branch="feature/calc",
            base_branch="main",
            commit_sha="abcdef1",
            base_commit_sha="1234567",
            is_branch_targeted=True,
            total_files_changed=1,
            files=[
                ChangedFile(path="math_ops.py", status="MODIFIED", modified_lines=[1, 2]),
            ],
        )

        candidates = auditor.generate_candidate_pairs(fake_delta)
        assert len(candidates) >= 1
        # Test candidate discovered
        assert any(c["artifact_2"]["path"] == "test_math_ops.py" for c in candidates)


def test_verbatim_verification_invariant():
    """
    Mathematical Invariant:
    A drift is confirmed IF AND ONLY IF fact_1 is a verbatim substring of content_1
    AND fact_2 is a verbatim substring of content_2.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        f1 = root / "app.py"
        f1.write_text("import jose\ndef verify():\n    pass\n")

        f2 = root / "requirements.txt"
        f2.write_text("fastapi==0.110.0\npytest==8.0.0\n")

        auditor = DriftAuditorAgent(workspace_path=root)

        # 1. Valid Grounded Case: Both quotes are exact verbatim substrings
        grounded_pred = DriftPrediction(
            drift_present=True,
            drift_type="dependency_vs_code",
            extracted_fact_1="import jose",
            extracted_fact_2="fastapi==0.110.0",
            artifact_1_lines="1",
            artifact_2_lines="1",
            evidence="jose is imported but not in requirements.txt",
            expected_fix="Add jose to requirements.txt",
        )
        res_grounded = auditor.verifier.verify(grounded_pred, f1.read_text(), f2.read_text())
        assert res_grounded.status == "Confirmed Drift"

        # 2. Hallucinated Case: Model fabricates a quote not in the file
        hallucinated_pred = DriftPrediction(
            drift_present=True,
            drift_type="dependency_vs_code",
            extracted_fact_1="import nonexistent_jwt_lib_xyz",
            extracted_fact_2="fastapi==0.110.0",
            evidence="Invented library",
        )
        res_hallucinated = auditor.verifier.verify(hallucinated_pred, f1.read_text(), f2.read_text())
        # Must be rejected because F1 is not in C1
        assert res_hallucinated.status == "No Drift"


def test_coordinator_run_drift_audit():
    import subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=root, check=True)

        (root / ".driftguard.yml").write_text("version: '1.0'\n")
        (root / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True)

        coord = CoordinatorAgent(workspace_path=root)

        # Execute drift audit on clean state
        state = coord.run_drift_audit()
        assert state.audit_status in ("READY_FOR_AUDIT", "AUDIT_COMPLETED", "SKIPPED")
        d = state.to_dict()
        assert "audit_status" in d

