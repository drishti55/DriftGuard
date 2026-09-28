"""
DriftGuard Output Validator
Pydantic models for structured LLM output and robust JSON extraction.
"""

import json
import re
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class DriftPrediction(BaseModel):
    """Structured prediction from the LLM for a single drift analysis."""
    drift_present: bool = Field(description="Whether a drift/inconsistency was detected")
    drift_type: str = Field(description="Category of drift detected")
    artifact_1_lines: str = Field(default="N/A", description="Line numbers for evidence in Artifact 1")
    artifact_2_lines: str = Field(default="N/A", description="Line numbers for evidence in Artifact 2")
    extracted_fact_1: str = Field(default="", description="Exact verbatim snippet from Artifact 1")
    extracted_fact_2: str = Field(default="", description="Exact verbatim snippet from Artifact 2")
    evidence: str = Field(default="", description="One-sentence description of the concrete contradiction")
    # Optional legacy / research fields — not shown in product UI
    severity: str = Field(default="none", description="Optional severity hint from model")
    expected_fix: str = Field(default="", description="Optional suggested correction")
    confidence: Optional[float] = Field(default=None, description="Optional model confidence 0-1")

    @field_validator("drift_type")
    @classmethod
    def validate_drift_type(cls, v: str) -> str:
        valid = {
            "documentation_vs_code", "test_vs_code", "api_spec_vs_code",
            "dependency_vs_code", "ci_vs_project", "docker_vs_project",
            "build_config_vs_project", "configuration_vs_code", "no_drift",
        }
        v_clean = v.strip().lower()
        if v_clean in valid:
            return v_clean
        for t in valid:
            if v_clean.replace(" ", "_").replace("-", "_") in t or t in v_clean:
                return t
        return v_clean

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"none", "low", "medium", "high"}
        v_clean = v.strip().lower()
        if v_clean in valid:
            return v_clean
        return "none"


class ParseResult:
    """Result of attempting to parse LLM output into a DriftPrediction."""

    def __init__(self, prediction: Optional[DriftPrediction] = None,
                 raw_output: str = "", error: Optional[str] = None,
                 parse_method: str = "none"):
        self.prediction = prediction
        self.raw_output = raw_output
        self.error = error
        self.parse_method = parse_method
        self.success = prediction is not None

    def __repr__(self):
        if self.success:
            return f"ParseResult(success=True, method={self.parse_method})"
        return f"ParseResult(success=False, error={self.error})"


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Attempt to extract a JSON object from potentially malformed LLM output.
    Tries multiple strategies in order of reliability.
    """
    if not text or not text.strip():
        return None

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON in code blocks ```json ... ```
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find the first { ... } block (greedy match for outermost braces)
    brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: More aggressive — find { and last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try fixing common issues
            candidate = candidate.replace("'", '"')
            candidate = re.sub(r',\s*}', '}', candidate)  # Trailing commas
            candidate = re.sub(r',\s*]', ']', candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Strategy 5: Line-by-line key-value extraction
    result = {}
    for line in text.split('\n'):
        for key in ['drift_present', 'drift_type', 'severity', 'evidence', 'expected_fix', 'confidence']:
            pattern = rf'["\']?{key}["\']?\s*[:=]\s*(.+?)(?:,?\s*$)'
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                val = match.group(1).strip().strip('"\'').strip(',')
                if key == 'drift_present':
                    result[key] = val.lower() in ('true', '1', 'yes')
                elif key == 'confidence':
                    try:
                        result[key] = float(val)
                    except ValueError:
                        pass
                else:
                    result[key] = val

    if 'drift_present' in result and 'drift_type' in result:
        return result

    return None


def validate_output(raw_output: str) -> ParseResult:
    """
    Parse and validate LLM output into a DriftPrediction.
    Tries multiple extraction strategies and validates with Pydantic.
    """
    if not raw_output or not raw_output.strip():
        return ParseResult(raw_output=raw_output, error="Empty output from LLM")

    # Try JSON extraction
    extracted = extract_json_from_text(raw_output)
    if extracted is None:
        return ParseResult(
            raw_output=raw_output,
            error="Could not extract JSON from LLM output"
        )

    # Normalize field names (handle variations)
    normalized = {}
    field_aliases = {
        'drift_present': ['drift_present', 'driftPresent', 'drift_detected', 'has_drift', 'inconsistency_detected'],
        'drift_type': ['drift_type', 'driftType', 'type', 'category', 'drift_category'],
        'severity': ['severity', 'level', 'severity_level'],
        'artifact_1_lines': ['artifact_1_lines', 'artifact1_lines', 'lines_1'],
        'artifact_2_lines': ['artifact_2_lines', 'artifact2_lines', 'lines_2'],
        'extracted_fact_1': ['extracted_fact_1', 'fact_1', 'snippet_1'],
        'extracted_fact_2': ['extracted_fact_2', 'fact_2', 'snippet_2'],
        'evidence': ['evidence', 'explanation', 'reasoning', 'description', 'details'],
        'expected_fix': ['expected_fix', 'expectedFix', 'fix', 'suggestion', 'recommended_fix', 'suggested_fix'],
        'confidence': ['confidence', 'score', 'confidence_score'],
    }

    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            if alias in extracted:
                val = extracted[alias]
                if canonical == 'drift_present' and isinstance(val, str):
                    val = val.lower() in ('true', '1', 'yes')
                normalized[canonical] = val
                break

    # Ensure required fields
    if 'drift_present' not in normalized:
        normalized['drift_present'] = True  # Default to detected if type/evidence present
    if 'drift_type' not in normalized:
        if not normalized.get('drift_present', True):
            normalized['drift_type'] = 'no_drift'
        else:
            # Try to infer drift_type from evidence or other extracted keys
            inferred = _infer_drift_type(extracted, normalized.get('evidence', ''))
            if inferred:
                normalized['drift_type'] = inferred
            else:
                # Last resort: check any remaining keys in extracted dict
                for k, v in extracted.items():
                    if isinstance(v, str) and v.strip() in {
                        "dependency_vs_code", "test_vs_code", "documentation_vs_code",
                        "api_spec_vs_code", "ci_vs_project", "docker_vs_project",
                        "build_config_vs_project", "configuration_vs_code", "no_drift",
                    }:
                        normalized['drift_type'] = v.strip()
                        break
                else:
                    normalized['drift_type'] = 'dependency_vs_code'  # Most common default
    if 'evidence' not in normalized:
        normalized['evidence'] = extracted.get('evidence', 'No evidence provided.')

    # Handle drift_present=False consistency
    if not normalized.get('drift_present', True):
        normalized['drift_type'] = 'no_drift'

    # Validate with Pydantic
    try:
        prediction = DriftPrediction(**normalized)
        return ParseResult(
            prediction=prediction,
            raw_output=raw_output,
            parse_method="json_extraction"
        )
    except Exception as e:
        return ParseResult(
            raw_output=raw_output,
            error=f"Pydantic validation failed: {e}"
        )


def _infer_drift_type(extracted: dict, evidence: str) -> Optional[str]:
    """
    Try to infer drift_type from evidence text or other fields.
    """
    text = (evidence + " " + json.dumps(extracted)).lower()

    patterns = {
        "dependency_vs_code": ["import", "module", "package", "dependency", "require", "undeclared", "missing module"],
        "test_vs_code": ["test", "spec", "assert", "mock", "fixture"],
        "documentation_vs_code": ["readme", "doc", "documentation", "example", "usage"],
        "api_spec_vs_code": ["openapi", "swagger", "endpoint", "api spec"],
        "ci_vs_project": ["ci", "workflow", "pipeline", "github action", "travis"],
        "docker_vs_project": ["docker", "container", "dockerfile", "compose"],
        "build_config_vs_project": ["build", "makefile", "cmake", "webpack", "config"],
        "configuration_vs_code": ["config", "settings", "environment", "env"],
    }

    best_match = None
    best_count = 0
    for drift_type, keywords in patterns.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_match = drift_type

    return best_match if best_count > 0 else None
