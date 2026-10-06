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
from app.agents.drift_auditor import DriftAuditorAgent, DriftAuditReport, ConfirmedDrift
from app.agents.reflection_agent import CompilerReflectionAgent, RepairReport
from app.agents.repair_engineer import SandboxedRepairEngineer
from app.sandbox import get_sandbox_runner

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorSessionState:
    """Central session blackboard holding perception reports, audits, and execution status."""
    workspace_path: str
    config: DriftGuardConfig
    delta_report: GitDeltaReport
    stack_report: StackReport
    audit_report: Optional[DriftAuditReport] = None
    audit_status: str = "INITIALIZED"  # 'INITIALIZED', 'SKIPPED', 'READY_FOR_AUDIT', 'AUDIT_COMPLETED'
    messages: List[str] = field(default_factory=list)
    repair_report: Optional[RepairReport] = None
    repair_status: str = "NOT_STARTED"

    def to_dict(self) -> Dict:
        res = {
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
            "repair_status": self.repair_status,
        }
        if self.audit_report:
            res["audit_report"] = self.audit_report.to_dict()
        if self.repair_report:
            res["repair_report"] = self.repair_report.to_dict()
        return res


class CoordinatorAgent:
    """
    Coordinates repository perception, code intelligence, and consistency audits.
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
        self.drift_auditor = DriftAuditorAgent(self.workspace_path)

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

    def run_drift_audit(
        self,
        base_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        max_candidates: Optional[int] = None,
        model: Optional[str] = None,
    ) -> CoordinatorSessionState:
        """
        Executes Phase 2 code intelligence and drift audit:
        1. Ingests delta & stack perception.
        2. Queries Tree-sitter & SCIP for cross-artifact candidates.
        3. Audits candidates via OmniRoute gateway.
        4. Enforces verbatim verification.
        """
        state = self.run_initial_perception(base_branch=base_branch, target_branch=target_branch)
        if state.audit_status != "READY_FOR_AUDIT":
            return state

        audit_report = self.drift_auditor.audit_delta(
            delta_report=state.delta_report,
            max_candidates=max_candidates,
            model=model,
        )
        state.audit_report = audit_report
        state.audit_status = "AUDIT_COMPLETED"
        state.messages.append(
            f"Audit completed: {len(audit_report.confirmed_drifts)} confirmed drift(s) across "
            f"{audit_report.total_candidates} candidate pair(s)."
        )
        return state


    def run_repair_workflow(
        self,
        confirmed_drifts: List[ConfirmedDrift],
        max_attempts: Optional[int] = None,
    ) -> CoordinatorSessionState:
        state = self.run_initial_perception()
        if state.audit_status == "SKIPPED":
            state.repair_status = "SKIPPED"
            return state
        if not confirmed_drifts:
            state.repair_status = "NO_DRIFT"
            return state
        if not self.config.repair.enabled:
            state.repair_status = "DISABLED"
            return state

        runner = get_sandbox_runner(self.workspace_path, self.config)
        engineer = SandboxedRepairEngineer(self.workspace_path)
        reflection = CompilerReflectionAgent(max_attempts or self.config.repair.max_attempts)
        drift = confirmed_drifts[0]

        def generate_and_execute(context: str):
            candidate, results = engineer.apply_and_validate(
                drift, runner, state.stack_report.effective_build_matrix, context
            )
            return candidate.patch, results

        state.repair_status = "IN_PROGRESS"
        try:
            state.repair_report = reflection.run(generate_and_execute)
            state.repair_status = "VERIFIED" if state.repair_report.verified else "FAILED"
        finally:
            runner.cleanup()
        return state
