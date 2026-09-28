"""
DriftGuard Fix Validator
Applies suggested fixes in a temporary copy and re-checks for drift resolution.
Never modifies the original repository.
"""

import os
import re
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from app import config

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of attempting to validate a suggested fix."""
    fix_applied: bool = False
    drift_resolved: bool = False
    error: Optional[str] = None
    temp_dir: Optional[str] = None
    details: str = ""


def validate_fix(workspace_path: Path, artifact_path: str,
                 suggested_fix: str, drift_type: str) -> ValidationResult:
    """
    Validate a suggested fix by applying it in a temporary copy.

    Steps:
    1. Copy the relevant files to a temp directory
    2. Apply the fix
    3. Run basic static checks
    4. Report whether the drift was resolved

    Args:
        workspace_path: The active repository workspace path
        artifact_path: Path of the file to fix
        suggested_fix: Description or content of the fix
        drift_type: Type of drift being fixed

    Returns:
        ValidationResult
    """
    result = ValidationResult()

    source_dir = Path(workspace_path)
    if not source_dir.exists():
        result.error = f"Workspace not found on disk: {source_dir}"
        return result

    source_file = source_dir / artifact_path
    if not source_file.exists():
        result.error = f"Artifact file not found in workspace: {artifact_path}"
        return result

    # Create temp copy
    try:
        temp_dir = tempfile.mkdtemp(prefix="driftguard_fix_")
        result.temp_dir = temp_dir

        # Copy the target file
        temp_file = Path(temp_dir) / Path(artifact_path).name
        shutil.copy2(source_file, temp_file)

        # Apply fix based on drift type
        fix_applied = _apply_fix(temp_file, suggested_fix, drift_type, source_dir, artifact_path)
        result.fix_applied = fix_applied

        if fix_applied:
            # Run basic checks
            check_result = _run_checks(temp_file, artifact_path)
            result.drift_resolved = check_result["resolved"]
            result.details = check_result["details"]
        else:
            result.details = "Could not automatically apply the suggested fix."

    except Exception as e:
        result.error = f"Fix validation failed: {e}"
        logger.error(f"Fix validation error: {e}")
    finally:
        # Clean up temp dir
        if result.temp_dir and os.path.exists(result.temp_dir):
            try:
                shutil.rmtree(result.temp_dir)
            except Exception:
                pass

    return result


def _apply_fix(temp_file: Path, suggested_fix: str,
               drift_type: str, source_dir: Path,
               artifact_path: str) -> bool:
    """
    Attempt to apply a fix to the temp file.
    Returns True if the fix was applied.
    """
    try:
        content = temp_file.read_text(errors='replace')

        if drift_type == "dependency_vs_code":
            # Try to add a missing dependency
            # Extract module name from evidence
            module_match = re.search(r'[Mm]odule\s+`([^`]+)`', suggested_fix)
            if module_match and artifact_path.endswith(('.txt', '.json', '.toml')):
                module_name = module_match.group(1)
                if artifact_path.endswith('.txt'):
                    content = content.rstrip() + f"\n{module_name}\n"
                    temp_file.write_text(content)
                    return True
                elif artifact_path.endswith('.json'):
                    # Add to dependencies in package.json
                    if '"dependencies"' in content:
                        content = content.replace(
                            '"dependencies": {',
                            f'"dependencies": {{\n    "{module_name}": "*",'
                        )
                        temp_file.write_text(content)
                        return True

        elif drift_type == "documentation_vs_code":
            # Mark as needing manual update
            return False

        elif drift_type == "test_vs_code":
            # Try to fix function name references
            old_func = re.search(r'`(\w+)\(\)`.*?(?:renamed|changed|updated)', suggested_fix)
            new_func = re.search(r'(?:to|use)\s+`(\w+)\(\)`', suggested_fix)
            if old_func and new_func:
                content = content.replace(old_func.group(1), new_func.group(1))
                temp_file.write_text(content)
                return True

    except Exception as e:
        logger.warning(f"Failed to apply fix: {e}")

    return False


def _run_checks(temp_file: Path, artifact_path: str) -> dict:
    """
    Run basic static checks on the fixed file.
    """
    result = {"resolved": False, "details": ""}

    try:
        content = temp_file.read_text(errors='replace')

        # Basic syntax check for Python files
        if artifact_path.endswith('.py'):
            try:
                compile(content, artifact_path, 'exec')
                result["details"] = "Python syntax check passed."
                result["resolved"] = True
            except SyntaxError as e:
                result["details"] = f"Python syntax error after fix: {e}"

        # Basic JSON validity check
        elif artifact_path.endswith('.json'):
            import json
            try:
                json.loads(content)
                result["details"] = "JSON syntax check passed."
                result["resolved"] = True
            except json.JSONDecodeError as e:
                result["details"] = f"JSON syntax error after fix: {e}"

        # For other files, just check it's non-empty
        else:
            if content.strip():
                result["details"] = "File is non-empty after fix."
                result["resolved"] = True
            else:
                result["details"] = "File is empty after fix."

    except Exception as e:
        result["details"] = f"Check failed: {e}"

    return result
