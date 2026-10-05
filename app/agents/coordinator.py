"""
DriftGuard Coordinator Agent
Root coordinator orchestrating delta perception, stack detection, and consistency audits.
Maintains session state and governs execution against .driftguard.yml policies.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.config_schema import DriftGuardConfig
from app.agents.delta_scanner import GitDeltaScanner, GitDeltaReport
from app.agents.stack_detector import StackDetector, StackReport

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorSessionState:
    """Central session blackboard holding perception reports and execution status."""
    workspace_path: str
    config: DriftGuardConfig
    delta_report: GitDeltaReport
    stack_report: StackReport
    audit_status: str = "INITIALIZED"  # 'INITIALIZED', 'SKIPPED', 'READY_FOR_AUDIT'
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "workspace_path": self.workspace_path,
            "audit_status": self.audit_status,
            "branch": self.delta_report.current_branch,
            "is_branch_targeted": self.delta_report.is_branch_targeted,
            "skip_reason": self.delta_report.skip_reason,
            "total_files_changed": self.delta_report.total_files_changed,
            "detected_languages": self.stack_report.detected_languages,
            "is_polyglot": self.stack_report.is_polyglot,
            "components": [c.name for c in self.stack_report.components],
            "effective_build_matrix": {
                k: v.model_dump() for k, v in self.stack_report.effective_build_matrix.items()
            },
            "messages": self.messages,
        }


class CoordinatorAgent:
    """
    Coordinates repository perception and enforces governance rules.
    """

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        self.workspace_path = Path(workspace_path or Path.cwd()).resolve()
        self.config = DriftGuardConfig.load(config_path or (self.workspace_path / ".driftguard.yml"))
        self.delta_scanner = GitDeltaScanner(self.workspace_path, self.config)
        self.stack_detector = StackDetector(self.workspace_path, self.config)

    def run_initial_perception(
        self,
        base_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
    ) -> CoordinatorSessionState:
        """
        Execute Phase 1 perception: scan git delta and auto-detect tech stack.
        """
        logger.info(f"Initializing Coordinator perception for workspace: {self.workspace_path}")
        messages: List[str] = []

        # 1. Delta Scan
        delta = self.delta_scanner.scan_delta(
            base_branch=base_branch,
            target_branch=target_branch,
        )
        messages.append(f"Scanned branch '{delta.current_branch}' against base '{delta.base_branch}'.")

        # 2. Stack Detection
        stack = self.stack_detector.detect_stack()
        lang_str = ", ".join(stack.detected_languages) if stack.detected_languages else "Unknown"
        messages.append(f"Detected stack ({lang_str}) with {len(stack.components)} component(s).")

        status = "READY_FOR_AUDIT"
        if not delta.is_branch_targeted:
            status = "SKIPPED"
            messages.append(delta.skip_reason or "Branch skipped by configuration.")

        return CoordinatorSessionState(
            workspace_path=str(self.workspace_path),
            config=self.config,
            delta_report=delta,
            stack_report=stack,
            audit_status=status,
            messages=messages,
        )
