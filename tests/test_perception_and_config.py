"""
DriftGuard Architecture & Perception Foundation Tests
Validates .driftguard.yml schema, GitDeltaScanner, StackDetector, and CoordinatorAgent.
"""

import tempfile
from pathlib import Path

from app.config_schema import DriftGuardConfig
from app.agents.delta_scanner import GitDeltaScanner
from app.agents.stack_detector import StackDetector
from app.agents.coordinator import CoordinatorAgent


def test_driftguard_config_defaults():
    """Verify safe default configuration when no file is present."""
    cfg = DriftGuardConfig()
    assert cfg.version == "1.0"
    assert "main" in cfg.branches.include
    assert cfg.build_matrix.auto_detect is True
    assert cfg.sandbox.runtime == "docker"
    assert cfg.repair.max_attempts == 3
    assert cfg.repair.enabled is True
    assert cfg.pull_request.auto_create is True


def test_driftguard_config_load_and_dump():
    """Verify loading from .driftguard.yml and YAML serialization."""
    cfg = DriftGuardConfig.load()
    assert cfg.version == "1.0"
    assert "backend" in cfg.build_matrix.overrides
    assert "frontend" in cfg.build_matrix.overrides
    assert cfg.build_matrix.overrides["backend"].test_command == "pytest tests/"

    yaml_str = cfg.to_yaml()
    assert "version: '1.0'" in yaml_str or "version: \"1.0\"" in yaml_str
    assert "backend" in yaml_str


def test_git_delta_scanner_live_repo():
    """Verify delta scanner accurately inspects the current repository."""
    scanner = GitDeltaScanner()
    assert scanner.is_git_repo() is True
    branch = scanner.get_current_branch()
    assert branch != ""

    # Test branch inclusion logic
    assert scanner.is_branch_allowed("main") is True
    assert scanner.is_branch_allowed("feature/auth") is True
    assert scanner.is_branch_allowed("docs-only/typos") is False

    # Test delta against HEAD~1
    report = scanner.scan_delta(base_branch="HEAD~1")
    assert report.is_branch_targeted is True
    assert report.total_files_changed > 0
    assert report.commit_sha != ""


def test_stack_detector_live_repo():
    """Verify stack detector identifies Python and TypeScript components in DriftGuard."""
    detector = StackDetector()
    report = detector.detect_stack()

    assert report.is_polyglot is True
    assert "Python" in report.detected_languages
    assert "TypeScript" in report.detected_languages

    comp_names = [c.name for c in report.components]
    assert "backend" in comp_names
    assert "frontend" in comp_names

    # Verify effective build matrix merges overrides
    matrix = report.effective_build_matrix
    assert "frontend" in matrix
    assert "backend" in matrix
    assert matrix["frontend"].build_command == "npm run build"
    assert matrix["backend"].test_command == "pytest tests/"


def test_stack_detector_synthetic_node_component():
    """Verify stack detector correctly inspects a standalone synthetic Node project."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            '{"name": "test-app", "dependencies": {"next": "14.0.0"}, "scripts": {"build": "next build"}}'
        )

        detector = StackDetector(workspace_path=tmp_path)
        report = detector.detect_stack()

        assert "JavaScript" in report.detected_languages or "TypeScript" in report.detected_languages
        assert len(report.components) == 1
        comp = report.components[0]
        assert "Next.js" in comp.frameworks
        assert comp.inferred_build_command == "npm run build"


def test_coordinator_agent_initial_perception():
    """Verify the root coordinator agent ties perception, delta, and stack detection cleanly."""
    coord = CoordinatorAgent()
    state = coord.run_initial_perception(base_branch="HEAD~1")

    assert state.audit_status == "READY_FOR_AUDIT"
    assert state.delta_report.total_files_changed > 0
    assert len(state.stack_report.components) >= 2
    assert len(state.messages) >= 2

    state_dict = state.to_dict()
    assert state_dict["branch"] == "main"
    assert state_dict["is_branch_targeted"] is True
    assert "backend" in state_dict["effective_build_matrix"]
