"""
DriftGuard Evidence Verifier
Cross-references LLM-generated citations and snippets against actual file content.

The three output states are:
  "Confirmed Drift"  — system independently verified the contradiction in the repository
  "No Drift"         — system analyzed the artifacts and found no verifiable contradiction
  "Analysis Failed"  — a technical error prevented analysis (file unreadable, LLM failed, etc.)

Nothing else. No partial, unverified, or rejected states.
"""

import re
import logging
from dataclasses import dataclass

from app.analysis.output_validator import DriftPrediction

logger = logging.getLogger(__name__)


_MISSING_SENTINELS = frozenset(["", "none", "n/a", "not found", "not applicable", "empty", "no evidence", "no documentation", "missing"])


@dataclass
class EvidenceVerificationResult:
    """Result of verifying the LLM's evidence."""
    status: str  # "Confirmed Drift", "No Drift", "Analysis Failed"
    details: str
    artifact_1_verified: bool = False
    artifact_2_verified: bool = False
    real_evidence_1: str = ""  # Lines extracted directly from the repository file
    real_evidence_2: str = ""  # Lines extracted directly from the repository file


def _extract_lines_from_content(content: str, lines_str: str) -> str:
    """
    Extract specific lines from file content using a line-range string like "42", "42-45", "42,45".
    Returns an empty string if extraction fails.
    """
    if not lines_str or lines_str.strip().lower() in _MISSING_SENTINELS:
        return ""

    lines = content.split('\n')
    try:
        nums = []
        for part in lines_str.replace(' ', '').split(','):
            if '-' in part:
                a, b = part.split('-', 1)
                nums.extend(range(int(a), int(b) + 1))
            else:
                nums.append(int(part))

        extracted = []
        for n in sorted(set(nums)):
            if 1 <= n <= len(lines):
                extracted.append(f"L{n}: {lines[n - 1]}")
        return "\n".join(extracted) if extracted else ""
    except Exception:
        return ""


class EvidenceVerifier:
    """
    Verifies drift claims against actual repository file content.

    Logic:
    1. If any file could not be read → Analysis Failed
    2. If the model says no drift → No Drift
    3. If the model claims drift but provides no verbatim quotes → No Drift
    4. Independently verify each quoted snippet against the file content
    5. Both snippets must be found → Confirmed Drift
    6. Either snippet is not found → No Drift (hallucinated evidence)
    """

    def verify(
        self,
        prediction: DriftPrediction,
        content_1: str,
        content_2: str,
    ) -> EvidenceVerificationResult:
        FILE_ERROR_MARKERS = {"[File not found on disk]", "[Could not read file]", "[File not found]"}

        # Step 1 — technical error: files unreadable
        if content_1 in FILE_ERROR_MARKERS or content_2 in FILE_ERROR_MARKERS:
            missing = []
            if content_1 in FILE_ERROR_MARKERS:
                missing.append("Artifact 1")
            if content_2 in FILE_ERROR_MARKERS:
                missing.append("Artifact 2")
            return EvidenceVerificationResult(
                status="Analysis Failed",
                details=f"Could not read {' and '.join(missing)} from the repository.",
            )

        # Step 2 — model says no drift
        if not prediction.drift_present or prediction.drift_type == "no_drift":
            return EvidenceVerificationResult(
                status="No Drift",
                details="The model determined no inconsistency exists between the artifacts.",
            )

        fact_1 = (prediction.extracted_fact_1 or "").strip()
        fact_2 = (prediction.extracted_fact_2 or "").strip()

        # Step 3 — LLM provided no concrete quotes
        if fact_1.lower() in _MISSING_SENTINELS or fact_2.lower() in _MISSING_SENTINELS:
            return EvidenceVerificationResult(
                status="No Drift",
                details="The model did not provide specific verbatim quotes from both artifacts.",
            )

        # Step 4 — independently verify each snippet
        a1_ok = self._snippet_in_content(fact_1, content_1)
        a2_ok = self._snippet_in_content(fact_2, content_2)

        # Step 5 — extract the real lines for display
        real_ev_1 = _extract_lines_from_content(content_1, prediction.artifact_1_lines)
        real_ev_2 = _extract_lines_from_content(content_2, prediction.artifact_2_lines)

        # If line extraction failed but snippet was verified, use the verified snippet as evidence
        if a1_ok and not real_ev_1:
            real_ev_1 = fact_1
        if a2_ok and not real_ev_2:
            real_ev_2 = fact_2

        # Step 6 — decide
        if a1_ok and a2_ok:
            return EvidenceVerificationResult(
                status="Confirmed Drift",
                details="Both cited snippets were independently found in the repository files.",
                artifact_1_verified=True,
                artifact_2_verified=True,
                real_evidence_1=real_ev_1,
                real_evidence_2=real_ev_2,
            )
        else:
            who = []
            if not a1_ok:
                who.append("Artifact 1 snippet")
            if not a2_ok:
                who.append("Artifact 2 snippet")
            return EvidenceVerificationResult(
                status="No Drift",
                details=f"{' and '.join(who)} could not be found in the repository. Possible hallucination — finding discarded.",
                artifact_1_verified=a1_ok,
                artifact_2_verified=a2_ok,
            )

    def _snippet_in_content(self, snippet: str, content: str) -> bool:
        """
        Check whether a snippet actually exists inside file content.
        Uses exact match → whitespace-normalised match → high-confidence keyword match.
        """
        if not snippet or snippet.lower() in _MISSING_SENTINELS:
            return False

        snippet_clean = snippet.strip()

        # 1. Exact substring match
        if snippet_clean in content:
            return True

        # 2. Whitespace-normalised match
        def ws_norm(t: str) -> str:
            return re.sub(r'\s+', ' ', t).strip()

        if ws_norm(snippet_clean) in ws_norm(content):
            return True

        # 3. High-confidence keyword match (≥ 85% of significant words present)
        words = [w.lower() for w in re.findall(r'\w+', snippet_clean) if len(w) > 3]
        if len(words) >= 2:
            content_lower = content.lower()
            hit = sum(1 for w in words if w in content_lower)
            if hit / len(words) >= 0.85:
                return True

        return False
