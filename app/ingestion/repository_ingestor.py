"""
DriftGuard Repository Ingestor
Handles dynamic loading of repositories from GitHub URLs, ZIP/Tar uploads, or local paths.
Provides a secure temporary workspace for analysis.
"""

import shutil
import tempfile
import logging
import subprocess
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IngestedRepository:
    """Represents a repository that has been loaded and is ready for analysis."""
    source_type: str  # "github", "archive", "local"
    workspace_path: Path
    original_source: str
    cleanup_func: Optional[Callable] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None

    def cleanup(self):
        """Clean up the temporary workspace if applicable."""
        if self.cleanup_func:
            try:
                self.cleanup_func()
                logger.info(f"Cleaned up temporary workspace: {self.workspace_path}")
            except Exception as e:
                logger.error(f"Failed to clean up workspace {self.workspace_path}: {e}")


class RepositoryIngestor:
    """
    Handles dynamic ingestion of repositories for analysis.
    """
    
    IGNORED_DIRS = {
        '.git', 'node_modules', 'venv', '.venv', 'env', '.env', 
        '__pycache__', 'build', 'dist', 'target', 'out', '.idea', '.vscode'
    }

    def __init__(self):
        pass

    def ingest_from_github(self, url: str, branch: Optional[str] = None, 
                           commit: Optional[str] = None) -> IngestedRepository:
        """
        Clone a GitHub repository into a temporary workspace.
        """
        if not url.startswith(("http://", "https://", "git@")):
            raise ValueError(f"Invalid Git URL: {url}")

        temp_dir = tempfile.mkdtemp(prefix="driftguard_gh_")
        logger.info(f"Cloning {url} into {temp_dir}...")

        try:
            cmd = ["git", "clone", "--depth", "1"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([url, temp_dir])
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            if commit:
                # If specific commit is requested, we need to fetch it
                logger.info(f"Fetching specific commit: {commit}")
                subprocess.run(["git", "fetch", "origin", commit], 
                               cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "checkout", commit], 
                               cwd=temp_dir, check=True, capture_output=True)

            # Get current commit sha
            res = subprocess.run(["git", "rev-parse", "HEAD"], 
                                 cwd=temp_dir, check=True, capture_output=True, text=True)
            current_commit = res.stdout.strip()
            
            # Get current branch
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                 cwd=temp_dir, check=False, capture_output=True, text=True)
            current_branch = res.stdout.strip() if res.returncode == 0 else branch

            def cleanup():
                shutil.rmtree(temp_dir, ignore_errors=True)

            return IngestedRepository(
                source_type="github",
                workspace_path=Path(temp_dir),
                original_source=url,
                cleanup_func=cleanup,
                branch=current_branch,
                commit_sha=current_commit
            )

        except subprocess.CalledProcessError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error(f"Git clone failed: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")

    def ingest_from_archive(self, archive_path: str) -> IngestedRepository:
        """
        Extract a ZIP or Tar archive into a temporary workspace securely.
        """
        path = Path(archive_path)
        if not path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        temp_dir = tempfile.mkdtemp(prefix="driftguard_archive_")
        logger.info(f"Extracting {archive_path} into {temp_dir}...")

        try:
            if path.suffix.lower() == '.zip':
                self._extract_zip_securely(path, Path(temp_dir))
            elif path.suffix.lower() in ('.tar', '.gz', '.bz2', '.xz', '.tgz'):
                self._extract_tar_securely(path, Path(temp_dir))
            else:
                raise ValueError(f"Unsupported archive format: {path.suffix}")

            # Detect if there's a single root directory in the archive
            actual_root = self._detect_actual_root(Path(temp_dir))

            def cleanup():
                shutil.rmtree(temp_dir, ignore_errors=True)

            return IngestedRepository(
                source_type="archive",
                workspace_path=actual_root,
                original_source=str(archive_path),
                cleanup_func=cleanup
            )
            
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to extract archive: {e}")

    def ingest_from_local(self, local_path: str) -> IngestedRepository:
        """
        Use an existing local directory. No cleanup required.
        """
        path = Path(local_path).resolve()
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Local repository directory not found: {local_path}")

        commit_sha = None
        branch = None

        # Check if it's a git repo
        if (path / ".git").exists():
            try:
                res = subprocess.run(["git", "rev-parse", "HEAD"], 
                                     cwd=path, check=False, capture_output=True, text=True)
                if res.returncode == 0:
                    commit_sha = res.stdout.strip()
                
                res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                     cwd=path, check=False, capture_output=True, text=True)
                if res.returncode == 0:
                    branch = res.stdout.strip()
            except Exception:
                pass

        return IngestedRepository(
            source_type="local",
            workspace_path=path,
            original_source=str(path),
            cleanup_func=None,  # Do not delete user's local directories!
            commit_sha=commit_sha,
            branch=branch
        )

    def _extract_zip_securely(self, archive_path: Path, dest_dir: Path):
        """Extract ZIP safely, ignoring known bad directories and absolute paths."""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member_info in zf.infolist():
                # Prevent path traversal
                if member_info.filename.startswith('/') or '..' in member_info.filename:
                    continue
                
                # Check if it belongs to ignored directories
                parts = Path(member_info.filename).parts
                if any(p in self.IGNORED_DIRS for p in parts):
                    continue
                    
                zf.extract(member_info, path=dest_dir)

    def _extract_tar_securely(self, archive_path: Path, dest_dir: Path):
        """Extract TAR safely, ignoring known bad directories and absolute paths."""
        with tarfile.open(archive_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.name.startswith('/') or '..' in member.name:
                    continue
                    
                parts = Path(member.name).parts
                if any(p in self.IGNORED_DIRS for p in parts):
                    continue
                    
                tf.extract(member, path=dest_dir)

    def _detect_actual_root(self, extract_dir: Path) -> Path:
        """
        Often archives contain a single root folder (e.g., repo-main/).
        If so, return that folder as the workspace root instead of the temp dir.
        """
        items = list(extract_dir.iterdir())
        if len(items) == 1 and items[0].is_dir():
            return items[0]
        return extract_dir
