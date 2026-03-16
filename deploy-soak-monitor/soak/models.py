"""Kubernetes resource models for simulation."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


class PodPhase(enum.Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class PodCondition(enum.Enum):
    NORMAL = "Normal"
    OOM_KILLED = "OOMKilled"
    CRASH_LOOP = "CrashLoopBackOff"


@dataclass
class Pod:
    name: str
    namespace: str
    deployment: str
    phase: PodPhase = PodPhase.PENDING
    condition: PodCondition = PodCondition.NORMAL
    restart_count: int = 0
    created_at: float = field(default_factory=time.time)
    logs: list[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return (
            self.phase == PodPhase.RUNNING
            and self.condition == PodCondition.NORMAL
            and self.restart_count == 0
        )


@dataclass
class Deployment:
    name: str
    namespace: str
    replicas: int = 2
    revision: int = 1
    pods: list[Pod] = field(default_factory=list)


@dataclass
class Event:
    """Kubernetes-style event."""

    type: str  # "ADDED", "MODIFIED", "DELETED"
    reason: str  # "DeploymentUpdated", "PodOOMKilled", etc.
    resource_kind: str  # "Deployment", "Pod"
    resource_name: str
    namespace: str
    message: str
    timestamp: float = field(default_factory=time.time)
