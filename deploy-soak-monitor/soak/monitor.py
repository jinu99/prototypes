"""Core soak monitoring logic."""

from __future__ import annotations

import asyncio
import time

from .cluster import SimulatedCluster
from .models import Event, PodCondition, PodPhase
from .patterns import PatternMatcher
from .reporter import Reporter


class SoakMonitor:
    """Watches deployments and monitors pods during the soak window."""

    def __init__(
        self,
        cluster: SimulatedCluster,
        namespace: str,
        duration: int = 900,  # 15 min default
        reporter: Reporter | None = None,
    ) -> None:
        self.cluster = cluster
        self.namespace = namespace
        self.duration = duration
        self.reporter = reporter or Reporter()
        self.matcher = PatternMatcher()
        self._detected_deployments: set[str] = set()
        self._anomaly_count = 0
        self._stop = False

        # Register event watcher
        self.cluster.add_watcher(self._on_event)

    def _on_event(self, event: Event) -> None:
        if event.namespace != self.namespace:
            return

        self.reporter.event(event)

        # Track deployment updates
        if (
            event.resource_kind == "Deployment"
            and event.reason == "DeploymentUpdated"
        ):
            self._detected_deployments.add(event.resource_name)

        # Track pods
        if event.resource_kind == "Pod":
            self.reporter.pods_monitored.add(event.resource_name)

        # Check for pod anomalies
        if event.resource_kind == "Pod":
            self._check_pod_event(event)

        # Check log errors via pattern matching (report highest severity only)
        if event.reason == "LogError":
            matches = self.matcher.match(event.message)
            if matches:
                priority = {"critical": 3, "error": 2, "warning": 1}
                best = max(matches, key=lambda m: priority.get(m.severity, 0))
                self.reporter.pattern_alert(event.resource_name, best)
                if best.severity in ("critical", "error"):
                    self._anomaly_count += 1
                    self.reporter.anomaly(
                        pod_name=event.resource_name,
                        anomaly_type=f"Log pattern [{best.pattern_name}]",
                        detail=best.matched_text,
                        deployment=self._guess_deployment(event.resource_name),
                        namespace=self.namespace,
                    )

    def _check_pod_event(self, event: Event) -> None:
        if event.reason == "PodOOMKilled":
            self._anomaly_count += 1
            self.reporter.anomaly(
                pod_name=event.resource_name,
                anomaly_type="OOMKilled",
                detail="Container killed by OOM killer",
                deployment=self._guess_deployment(event.resource_name),
                namespace=self.namespace,
            )
        elif event.reason == "BackOff":
            self._anomaly_count += 1
            self.reporter.anomaly(
                pod_name=event.resource_name,
                anomaly_type="CrashLoopBackOff",
                detail=event.message,
                deployment=self._guess_deployment(event.resource_name),
                namespace=self.namespace,
            )

    def _guess_deployment(self, pod_name: str) -> str:
        """Extract deployment name from pod name (name-revision-hash)."""
        parts = pod_name.rsplit("-", 2)
        return parts[0] if len(parts) >= 3 else pod_name

    async def run(self) -> bool:
        """Run the soak monitor. Returns True if all clear, False if issues."""
        self.reporter.banner(self.namespace, self.duration)

        print(f"  Watching namespace '{self.namespace}' for deployment changes...\n")

        start = time.time()
        last_progress = 0

        while not self._stop:
            elapsed = int(time.time() - start)
            if elapsed >= self.duration:
                break

            # Show progress every 2 seconds
            if elapsed - last_progress >= 2:
                self.reporter.soak_progress(elapsed, self.duration)
                last_progress = elapsed

            await asyncio.sleep(0.5)

        # Final report
        if self._anomaly_count == 0:
            self.reporter.all_clear(self.namespace, self.duration)
            return True
        else:
            self.reporter.summary_with_issues(self.namespace, self.duration)
            return False

    def stop(self) -> None:
        self._stop = True
