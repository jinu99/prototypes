"""Agent Mesh orchestrator.

Coordinates the full pipeline:
1. Route request via complexity classifier
2. Generate response from selected model
3. If small model was used, evaluate confidence
4. If confidence is low, escalate to large model
5. Return final result with full trace
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agent_mesh.models import (
    SMALL_MODEL, LARGE_MODEL, ModelResponse,
    generate, check_ollama_available,
)
from agent_mesh.router import ComplexityRouter, Complexity, RoutingDecision
from agent_mesh.confidence import (
    evaluate_confidence, ConfidenceResult, DEFAULT_CONFIDENCE_THRESHOLD,
)


@dataclass
class MeshStep:
    """One step in the mesh processing pipeline."""
    action: str
    model: str | None = None
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class MeshResult:
    """Final result from the agent mesh."""
    prompt: str
    final_response: str
    final_model: str
    was_escalated: bool
    routing: RoutingDecision | None = None
    confidence: ConfidenceResult | None = None
    steps: list[MeshStep] = field(default_factory=list)
    total_duration_ms: float = 0.0


class AgentMesh:
    """The main orchestrator for the local agent mesh."""

    def __init__(
        self,
        small_model: str = SMALL_MODEL,
        large_model: str = LARGE_MODEL,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self.small_model = small_model
        self.large_model = large_model
        self.confidence_threshold = confidence_threshold
        self.router = ComplexityRouter(
            small_model=small_model,
            large_model=large_model,
        )
        self.ollama_available = check_ollama_available()

    def process(self, prompt: str) -> MeshResult:
        """Process a request through the full mesh pipeline."""
        start = time.monotonic()
        steps: list[MeshStep] = []

        # Step 1: Route
        t0 = time.monotonic()
        routing = self.router.route(prompt)
        route_ms = (time.monotonic() - t0) * 1000
        steps.append(MeshStep(
            action="route",
            detail=f"{routing.complexity.value} (score: {routing.score:.2f})",
            model=routing.model,
            duration_ms=route_ms,
        ))

        # Step 2: Generate from routed model
        t0 = time.monotonic()
        response = generate(routing.model, prompt)
        gen_ms = (time.monotonic() - t0) * 1000
        steps.append(MeshStep(
            action="generate",
            model=routing.model,
            detail=f"{response.eval_count} tokens",
            duration_ms=gen_ms,
        ))

        was_escalated = False
        confidence = None

        # Step 3: If small model, evaluate confidence
        if routing.complexity == Complexity.SIMPLE:
            t0 = time.monotonic()
            confidence = evaluate_confidence(
                prompt, response, self.confidence_threshold,
            )
            eval_ms = (time.monotonic() - t0) * 1000
            steps.append(MeshStep(
                action="self_eval",
                model=routing.model,
                detail=f"confidence: {confidence.score:.2f}",
                duration_ms=eval_ms,
            ))

            # Step 4: Escalate if needed
            if confidence.should_escalate:
                was_escalated = True
                t0 = time.monotonic()
                escalation_response = generate(self.large_model, prompt)
                esc_ms = (time.monotonic() - t0) * 1000
                steps.append(MeshStep(
                    action="escalate",
                    model=self.large_model,
                    detail=(
                        f"confidence {confidence.score:.2f} "
                        f"< threshold {self.confidence_threshold}"
                    ),
                    duration_ms=esc_ms,
                ))
                response = escalation_response

        total_ms = (time.monotonic() - start) * 1000

        return MeshResult(
            prompt=prompt,
            final_response=response.text,
            final_model=response.model,
            was_escalated=was_escalated,
            routing=routing,
            confidence=confidence,
            steps=steps,
            total_duration_ms=total_ms,
        )
