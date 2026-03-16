"""Demo scenarios for soak monitor."""

from __future__ import annotations

import asyncio

from .cluster import SimulatedCluster


SCENARIOS = {
    "healthy": "Normal deployment — no issues, soak completes with ALL CLEAR",
    "oom": "Deployment where a pod gets OOMKilled after ~3 seconds",
    "crashloop": "Deployment entering CrashLoopBackOff with 3 restarts",
    "error_logs": "Deployment producing error logs (connection refused, panic, etc.)",
}


async def run_scenario(
    cluster: SimulatedCluster,
    scenario: str,
    namespace: str = "default",
    deploy_name: str = "web-api",
    delay: float = 2.0,
) -> None:
    """Set up initial deployment, then trigger a rolling update with the scenario."""

    # Step 1: Create initial deployment
    print(f"  Setting up initial deployment '{deploy_name}'...")
    await cluster.create_deployment(deploy_name, namespace, replicas=2)
    await asyncio.sleep(delay)

    # Step 2: Trigger rolling update with scenario
    print(f"\n  Triggering rolling update (scenario: {scenario})...\n")
    await cluster.rolling_update(deploy_name, namespace, scenario=scenario)

    # For healthy scenario, generate normal logs
    if scenario == "healthy":
        key = f"{namespace}/{deploy_name}"
        deploy = cluster.deployments[key]
        await cluster.generate_healthy_logs(deploy)
