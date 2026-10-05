"""
DriftGuard Git Delta Scanner Agent
Perceives incremental changes across git commits, branch comparisons, or uncommitted worktrees.
Extracts affected files, diff hunks, and line ranges to focus consistency analysis strictly on deltas.
"""

import fnmatch
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.config_schema import DriftGuardConfig

logger = logging.getLogger(__name__)


@dataclass
class ChangedFile:
    """Represents a single changed file within a git delta."""
    path: str
    status: str  # 'ADDED', 'MODIFIED', 'DELETED', 'RENAMED'
    old_path: Optional[str] = None
    diff_content: str = ""
    modified_lines: List[int] = field(default_factory=list)


@dataclass
class GitDeltaReport:
    """Complete summary of git changes across a commit range or branch comparison."""
    workspace_path: str
    current_branch: str
    base_branch: str
    commit_sha: str
    base_commit_sha: str
    is_branch_targeted: bool
    skip_reason: Optional[str] = None
    total_files_changed: int = 0
    added_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    files: List[ChangedFile] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "workspace_path": self.workspace_path,
            "current_branch": self.current_branch,
            "base_branch": self.base_branch,
            "commit_sha": self.commit_sha,
            "base_commit_sha": self.base_commit_sha,
            "is_branch_targeted": self.is_branch_targeted,
            "skip_reason": self.skip_reason,
            "total_files_changed": self.total_files_changed,
            "added_files": self.added_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "files": [
                {
                    "path": f.path,
                    "status": f.status,
                    "old_path": f.old_path,
                    "modified_line_count": len(f.modified_lines),
                }
                for f in self.files
            ],
        }


class GitDeltaScanner:
    """
    Scans a git repository workspace to extract incremental deltas.
    """

    def __init__(self, workspace_path: Optional[Path] = None, config: Optional[DriftGuardConfig] = None):
        self.workspace_path = Path(workspace_path or Path.cwd()).resolve()
        self.config = config or DriftGuardConfig.load(self.workspace_path / ".driftguard.yml")

    def _run_git(self, args: List[str], check: bool = True) -> str:
        """Run a git command in the workspace and return stdout."""
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=check,
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)} -> {e.stderr}")
            raise

    def is_git_repo(self) -> bool:
        """Check if workspace is a git repository."""
        try:
            res = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
            return res == "true"
        except Exception:
            return False

    def get_current_branch(self) -> str:
        """Get the current checked-out branch name or HEAD."""
        branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], check=False)
        return branch or "HEAD"

    def get_head_commit(self) -> str:
        """Get the current HEAD commit hash."""
        return self._run_git(["rev-parse", "HEAD"], check=False)

    def is_branch_allowed(self, branch_name: str) -> bool:
        """Evaluate if the branch matches inclusion/exclusion patterns in config."""
        for exc in self.config.branches.exclude:
            if fnmatch.fnmatch(branch_name, exc):
                return False

        for inc in self.config.branches.include:
            if fnmatch.fnmatch(branch_name, inc):
                return True

        return False

    def scan_delta(
        self,
        base_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        include_uncommitted: bool = True,
    ) -> GitDeltaReport:
        """
        Scan and compute the git delta.

        Args:
            base_branch: Base reference to compare against (e.g. 'main', 'origin/main', 'HEAD~1').
            target_branch: Branch to compare (defaults to current branch).
            include_uncommitted: If True and on working tree, includes uncommitted working tree diffs.
        """
        if not self.is_git_repo():
            raise ValueError(f"Workspace is not a valid git repository: {self.workspace_path}")

        current_branch = target_branch or self.get_current_branch()
        head_commit = self.get_head_commit()

        # Check branch policy
        is_targeted = self.is_branch_allowed(current_branch)
        skip_reason = None
        if not is_targeted:
            skip_reason = f"Branch '{current_branch}' is excluded by .driftguard.yml policy."

        # Determine sensible base comparison
        resolved_base = base_branch
        if not resolved_base:
            # Try to compare against origin/main, main, or HEAD~1
            candidates = ["origin/main", "main", "origin/master", "master"]
            for cand in candidates:
                try:
                    self._run_git(["rev-parse", "--verify", cand], check=True)
                    if cand != current_branch:
                        resolved_base = cand
                        break
                except Exception:
                    continue

            if not resolved_base:
                resolved_base = "HEAD~1"

        # Resolve base commit SHA
        try:
            base_commit = self._run_git(["rev-parse", resolved_base], check=True)
        except Exception:
            base_commit = head_commit

        report = GitDeltaReport(
            workspace_path=str(self.workspace_path),
            current_branch=current_branch,
            base_branch=resolved_base,
            commit_sha=head_commit,
            base_commit_sha=base_commit,
            is_branch_targeted=is_targeted,
            skip_reason=skip_reason,
        )

        if not is_targeted:
            return report

        # Extract name-status diff
        diff_args = ["diff", "--name-status"]
        if include_uncommitted and (not target_branch or target_branch == current_branch):
            diff_args.append(resolved_base)
        else:
            diff_args.append(f"{resolved_base}...{current_branch}")

        diff_output = self._run_git(diff_args, check=False)
        changed_files_map: Dict[str, ChangedFile] = {}

        if diff_output:
            for line in diff_output.splitlines():
                parts = line.strip().split("\t")
                if not parts:
                    continue
                code = parts[0][0]
                if code == "A":
                    path = parts[1]
                    cf = ChangedFile(path=path, status="ADDED")
                    report.added_files.append(path)
                    changed_files_map[path] = cf
                elif code == "M":
                    path = parts[1]
                    cf = ChangedFile(path=path, status="MODIFIED")
                    report.modified_files.append(path)
                    changed_files_map[path] = cf
                elif code == "D":
                    path = parts[1]
                    cf = ChangedFile(path=path, status="DELETED")
                    report.deleted_files.append(path)
                    changed_files_map[path] = cf
                elif code == "R":
                    old_p, new_p = parts[1], parts[2]
                    cf = ChangedFile(path=new_p, status="RENAMED", old_path=old_p)
                    report.modified_files.append(new_p)
                    changed_files_map[new_p] = cf

        # Extract unified diff content and modified line numbers per file
        for path, cf in changed_files_map.items():
            if cf.status == "DELETED":
                continue
            file_diff_args = ["diff", "-U0", resolved_base, "--", path]
            file_diff = self._run_git(file_diff_args, check=False)
            cf.diff_content = file_diff
            cf.modified_lines = self._parse_hunk_lines(file_diff)

        report.files = list(changed_files_map.values())
        report.total_files_changed = len(report.files)
        return report

    def _parse_hunk_lines(self, unified_diff: str) -> List[int]:
        """Parse added/modified line numbers from unified diff hunks (e.g. @@ -10,2 +12,4 @@)."""
        lines: Set[int] = set()
        for line in unified_diff.splitlines():
            if line.startswith("@@"):
                try:
                    plus_idx = line.find("+")
                    if plus_idx != -1:
                        chunk = line[plus_idx + 1 :].split(" ")[0]
                        if "," in chunk:
                            start_str, count_str = chunk.split(",")
                            start, count = int(start_str), int(count_str)
                        else:
                            start = int(chunk)
                            count = 1
                        for l in range(start, start + max(count, 1)):
                            lines.add(l)
                except Exception:
                    continue
        return sorted(lines)
