from app.agents.reflection_agent import CompilerReflectionAgent, patch_utility_score
from app.sandbox import SandboxExecutionResult


def test_patch_utility_score():
    assert patch_utility_score(1, 1, 0, 1) == 1.9


def test_reflection_stops_at_max_attempts():
    calls = []
    failed = SandboxExecutionResult(1, "", "compiler error", 0.1, "FAILED", "pytest")

    def attempt(context):
        calls.append(context)
        return "bad patch", [failed]

    report = CompilerReflectionAgent(3).run(attempt)
    assert len(calls) == 3
    assert report.status == "FAILED"
    assert "compiler error" in calls[1]
