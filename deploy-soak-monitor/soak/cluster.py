"""Simulated Kubernetes cluster for prototype testing."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Callable

from .models import Deployment, Event, Pod, PodCondition, PodPhase


class SimulatedCluster:
    """Simulates a K8s cluster with deployments, pods, and events."""

    def __init__(self) -> None:
        self.deployments: dict[str, Deployment] = {}
        self.events: list[Event] = []
        self._watchers: list[Callable[[Event], None]] = []
        self._log_generators: dict[str, asyncio.Task] = {}
        self._running = False

    def add_watcher(self, callback: Callable[[Event], None]) -> None:
        self._watchers.append(callback)

    def _emit(self, event: Event) -> None:
        self.events.append(event)
        for watcher in self._watchers:
            watcher(event)

    def _make_pod(self, deploy: Deployment, index: int) -> Pod:
        suffix = f"{random.randint(1000, 9999)}"
        return Pod(
            name=f"{deploy.name}-{deploy.revision}-{suffix}",
            namespace=deploy.namespace,
            deployment=deploy.name,
        )

    async def create_deployment(
        self, name: str, namespace: str, replicas: int = 2
    ) -> Deployment:
        deploy = Deployment(name=name, namespace=namespace, replicas=replicas)
        key = f"{namespace}/{name}"
        self.deployments[key] = deploy

        self._emit(Event(
            type="ADDED",
            reason="DeploymentCreated",
            resource_kind="Deployment",
            resource_name=name,
            namespace=namespace,
            message=f"Deployment {name} created with {replicas} replicas",
        ))

        # Create pods
        for i in range(replicas):
            pod = self._make_pod(deploy, i)
            deploy.pods.append(pod)
            await asyncio.sleep(0.3)
            pod.phase = PodPhase.RUNNING
            self._emit(Event(
                type="ADDED",
                reason="PodStarted",
                resource_kind="Pod",
                resource_name=pod.name,
                namespace=namespace,
                message=f"Pod {pod.name} started successfully",
            ))

        return deploy

    async def rolling_update(
        self, name: str, namespace: str, scenario: str = "healthy"
    ) -> None:
        """Simulate a rolling deployment update."""
        key = f"{namespace}/{name}"
        deploy = self.deployments.get(key)
        if not deploy:
            raise ValueError(f"Deployment {key} not found")

        deploy.revision += 1
        old_pods = list(deploy.pods)
        deploy.pods.clear()

        self._emit(Event(
            type="MODIFIED",
            reason="DeploymentUpdated",
            resource_kind="Deployment",
            resource_name=name,
            namespace=namespace,
            message=(
                f"Deployment {name} updated to revision {deploy.revision} "
                f"(rolling update started)"
            ),
        ))

        # Remove old pods
        for pod in old_pods:
            pod.phase = PodPhase.SUCCEEDED
            self._emit(Event(
                type="DELETED",
                reason="PodTerminated",
                resource_kind="Pod",
                resource_name=pod.name,
                namespace=namespace,
                message=f"Old pod {pod.name} terminated",
            ))

        # Create new pods based on scenario
        for i in range(deploy.replicas):
            pod = self._make_pod(deploy, i)
            deploy.pods.append(pod)
            await asyncio.sleep(0.5)
            pod.phase = PodPhase.RUNNING

            self._emit(Event(
                type="ADDED",
                reason="PodStarted",
                resource_kind="Pod",
                resource_name=pod.name,
                namespace=namespace,
                message=f"New pod {pod.name} started (revision {deploy.revision})",
            ))

        # Schedule failure scenarios
        if scenario == "oom":
            asyncio.create_task(self._inject_oom(deploy))
        elif scenario == "crashloop":
            asyncio.create_task(self._inject_crashloop(deploy))
        elif scenario == "error_logs":
            asyncio.create_task(self._inject_error_logs(deploy))

    async def _inject_oom(self, deploy: Deployment) -> None:
        await asyncio.sleep(3)
        if not deploy.pods:
            return
        pod = deploy.pods[0]
        pod.condition = PodCondition.OOM_KILLED
        pod.phase = PodPhase.FAILED
        pod.restart_count += 1
        pod.logs.append(
            f"[{_ts()}] FATAL: Out of memory — container killed by OOM killer"
        )
        self._emit(Event(
            type="MODIFIED",
            reason="PodOOMKilled",
            resource_kind="Pod",
            resource_name=pod.name,
            namespace=deploy.namespace,
            message=f"Pod {pod.name} OOMKilled (memory limit exceeded)",
        ))

    async def _inject_crashloop(self, deploy: Deployment) -> None:
        if not deploy.pods:
            return
        pod = deploy.pods[0]
        for i in range(3):
            await asyncio.sleep(2)
            pod.restart_count += 1
            pod.condition = PodCondition.CRASH_LOOP
            pod.phase = PodPhase.FAILED
            pod.logs.append(
                f"[{_ts()}] ERROR: Application crashed — exit code 137 (restart #{pod.restart_count})"
            )
            self._emit(Event(
                type="MODIFIED",
                reason="BackOff",
                resource_kind="Pod",
                resource_name=pod.name,
                namespace=deploy.namespace,
                message=(
                    f"Pod {pod.name} CrashLoopBackOff "
                    f"(restart count: {pod.restart_count})"
                ),
            ))

    async def _inject_error_logs(self, deploy: Deployment) -> None:
        error_messages = [
            "ERROR: Connection refused to database at 10.0.0.5:5432",
            "FATAL: Unable to acquire lock on resource /api/orders",
            "panic: runtime error: index out of range [3] with length 2",
            "Exception: NullPointerException in PaymentService.process()",
            "ERROR: Request timeout after 30000ms — upstream service unavailable",
        ]
        for pod in deploy.pods:
            await asyncio.sleep(2)
            for msg in error_messages[:3]:
                await asyncio.sleep(1)
                log_line = f"[{_ts()}] {msg}"
                pod.logs.append(log_line)
                self._emit(Event(
                    type="MODIFIED",
                    reason="LogError",
                    resource_kind="Pod",
                    resource_name=pod.name,
                    namespace=deploy.namespace,
                    message=log_line,
                ))

    async def generate_healthy_logs(self, deploy: Deployment) -> None:
        """Generate normal log output for healthy pods."""
        normal_logs = [
            "INFO: Server started on port 8080",
            "INFO: Health check passed",
            "INFO: Processing request GET /api/status — 200 OK (12ms)",
            "INFO: Database connection pool initialized (size=10)",
            "DEBUG: Cache hit ratio: 94.2%",
            "INFO: Processing request POST /api/orders — 201 Created (45ms)",
            "INFO: Metrics exported successfully",
        ]
        for pod in deploy.pods:
            for msg in normal_logs[:4]:
                pod.logs.append(f"[{_ts()}] {msg}")
                await asyncio.sleep(0.5)


def _ts() -> str:
    return time.strftime("%H:%M:%S")
