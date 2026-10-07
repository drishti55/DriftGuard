from app.config_schema import SandboxConfig
from app.sandbox import KubernetesJobGenerator, LocalProcessSandboxRunner


def test_local_sandbox_isolated_execution_and_cleanup(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    original = source / "value.txt"
    original.write_text("original")
    runner = LocalProcessSandboxRunner(source, timeout_seconds=1)
    sandbox = runner.provision()
    (sandbox / "value.txt").write_text("changed")
    assert original.read_text() == "original"
    result = runner.run_command("cat value.txt")
    assert result.status == "SUCCESS"
    assert result.stdout == "changed"
    runner.cleanup()
    assert not sandbox.exists()


def test_local_sandbox_timeout_and_patch(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    (source / "value.txt").write_text("before\n")
    runner = LocalProcessSandboxRunner(source, timeout_seconds=1)
    assert runner.apply_patch("""--- a/value.txt
+++ b/value.txt
@@ -1 +1 @@
-before
+after
""")
    assert runner.run_command("cat value.txt").stdout == "after\n"
    result = runner.run_command("sleep 2")
    assert result.status == "TIMEOUT"
    runner.cleanup()


def test_kubernetes_job_has_guardrails():
    yaml_text = KubernetesJobGenerator(SandboxConfig()).generate_yaml("pytest")
    assert "runAsNonRoot: true" in yaml_text
    assert "activeDeadlineSeconds: 120" in yaml_text
    assert "memory: 2Gi" in yaml_text
    assert "cpu: '2.0'" in yaml_text
