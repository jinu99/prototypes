"""Docker container status plugin — checks running containers via CLI."""

from __future__ import annotations

import subprocess
import json
from models import Alert, Severity


class DockerStatusPlugin:
    """Checks Docker container status using the docker CLI."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.containers: list[str] = config.get("containers", [])

    def poll(self) -> list[Alert]:
        alerts: list[Alert] = []

        # Check if docker is available
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=10,
            )
        except FileNotFoundError:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Docker not available",
                severity=Severity.INFO,
                message="Docker CLI is not installed or not in PATH",
            )]
        except subprocess.TimeoutExpired:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Docker timeout",
                severity=Severity.WARNING,
                message="Docker command timed out",
            )]

        if result.returncode != 0:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Docker error",
                severity=Severity.WARNING,
                message=f"Docker returned error: {result.stderr.strip()[:200]}",
            )]

        # Parse running containers
        running = {}
        for line in result.stdout.strip().splitlines():
            try:
                info = json.loads(line)
                running[info["Names"]] = info
            except (json.JSONDecodeError, KeyError):
                continue

        # Check expected containers
        if not self.containers:
            # No specific containers configured — report summary
            count = len(running)
            alerts.append(Alert(
                source=self.name,
                title=f"{self.name}: {count} container(s) found",
                severity=Severity.OK if count > 0 else Severity.INFO,
                message=", ".join(running.keys()) if running else "No containers running",
            ))
        else:
            for cname in self.containers:
                if cname in running:
                    status = running[cname].get("Status", "unknown")
                    if "Up" in status:
                        alerts.append(Alert(
                            source=self.name,
                            title=f"{cname}: Running",
                            severity=Severity.OK,
                            message=f"Status: {status}",
                            metadata={"container": cname},
                        ))
                    else:
                        alerts.append(Alert(
                            source=self.name,
                            title=f"{cname}: Not healthy",
                            severity=Severity.WARNING,
                            message=f"Status: {status}",
                            metadata={"container": cname},
                        ))
                else:
                    alerts.append(Alert(
                        source=self.name,
                        title=f"{cname}: Not found",
                        severity=Severity.CRITICAL,
                        message=f"Container '{cname}' is not running",
                        metadata={"container": cname},
                    ))
        return alerts
