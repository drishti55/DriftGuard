"""Declarative Kubernetes Job manifest generation."""

from typing import Optional
import yaml

from app.config_schema import SandboxConfig


class KubernetesJobGenerator:
    def __init__(self, config: Optional[SandboxConfig] = None, image: str = "python:3.12-slim"):
        self.config = config or SandboxConfig()
        self.image = image

    def build_job(self, command: str, job_name: str = "driftguard-repair", workspace_volume: str = "workspace") -> dict:
        network = {} if self.config.network_access == "unrestricted" else {"driftguard.network/access": self.config.network_access}
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": job_name, "labels": network},
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": self.config.timeout_seconds,
                "template": {
                    "metadata": {"labels": {"job-name": job_name, **network}},
                    "spec": {
                        "restartPolicy": "Never",
                        "securityContext": {"runAsNonRoot": True, "runAsUser": 1000},
                        "containers": [{
                            "name": "repair",
                            "image": self.image,
                            "command": ["sh", "-lc", command],
                            "workingDir": "/workspace",
                            "resources": {"limits": {"memory": self.config.memory_limit, "cpu": self.config.cpu_limit}},
                            "volumeMounts": [{"name": workspace_volume, "mountPath": "/workspace"}],
                        }],
                        "volumes": [{"name": workspace_volume, "persistentVolumeClaim": {"claimName": workspace_volume}}],
                    },
                },
            },
        }

    def generate_yaml(self, command: str, job_name: str = "driftguard-repair", workspace_volume: str = "workspace") -> str:
        return yaml.safe_dump(self.build_job(command, job_name, workspace_volume), sort_keys=False)
