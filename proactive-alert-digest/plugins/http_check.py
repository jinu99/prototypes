"""HTTP health check plugin — polls endpoints and reports status."""

from __future__ import annotations

import requests
from models import Alert, Severity


class HttpCheckPlugin:
    """Checks HTTP endpoints and generates alerts based on status codes."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.url: str = config["url"]
        self.timeout: int = config.get("timeout", 5)
        self.expected_status: int = config.get("expected_status", 200)

    def poll(self) -> list[Alert]:
        try:
            resp = requests.get(self.url, timeout=self.timeout)
            if resp.status_code == self.expected_status:
                return [Alert(
                    source=self.name,
                    title=f"{self.name}: OK",
                    severity=Severity.OK,
                    message=f"{self.url} returned {resp.status_code} ({resp.elapsed.total_seconds():.2f}s)",
                    metadata={"status_code": resp.status_code, "url": self.url},
                )]
            else:
                return [Alert(
                    source=self.name,
                    title=f"{self.name}: Unexpected status",
                    severity=Severity.WARNING,
                    message=f"{self.url} returned {resp.status_code} (expected {self.expected_status})",
                    metadata={"status_code": resp.status_code, "url": self.url},
                )]
        except requests.exceptions.ConnectionError:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Connection failed",
                severity=Severity.CRITICAL,
                message=f"Cannot reach {self.url}",
                metadata={"url": self.url},
            )]
        except requests.exceptions.Timeout:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Timeout",
                severity=Severity.CRITICAL,
                message=f"{self.url} did not respond within {self.timeout}s",
                metadata={"url": self.url},
            )]
        except Exception as e:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Error",
                severity=Severity.WARNING,
                message=f"Error checking {self.url}: {e}",
                metadata={"url": self.url},
            )]
