"""
Workflow vs Agent 결과를 비교하고 메트릭을 산출한다.
에스컬레이션 품질을 정량적으로 비교하는 핵심 모듈.
"""

from dataclasses import dataclass, asdict
from scenarios import Scenario
from workflow_engine import WorkflowResult
from agent_engine import AgentResult


@dataclass
class ScenarioComparison:
    scenario_id: str
    title: str
    complexity: str
    ground_truth_escalate: bool
    ground_truth_reason: str
    workflow_escalated: bool
    workflow_correct: bool
    agent_escalated: bool
    agent_correct: bool
    agent_confidence: float

    def to_dict(self):
        return asdict(self)


@dataclass
class AggregateMetrics:
    total: int
    # Workflow
    workflow_correct: int
    workflow_accuracy: float
    workflow_false_positives: int  # 불필요하게 에스컬레이션
    workflow_false_negatives: int  # 놓친 에스컬레이션
    workflow_fp_rate: float
    workflow_fn_rate: float
    # Agent
    agent_correct: int
    agent_accuracy: float
    agent_false_positives: int
    agent_false_negatives: int
    agent_fp_rate: float
    agent_fn_rate: float
    # 차이
    accuracy_delta: float  # agent - workflow (양수면 agent 우위)

    def to_dict(self):
        return asdict(self)


def compare_single(
    scenario: Scenario,
    workflow_result: WorkflowResult,
    agent_result: AgentResult,
) -> ScenarioComparison:
    """단일 시나리오의 Workflow vs Agent 결과를 비교."""
    return ScenarioComparison(
        scenario_id=scenario.id,
        title=scenario.title,
        complexity=scenario.complexity,
        ground_truth_escalate=scenario.should_escalate,
        ground_truth_reason=scenario.escalation_reason,
        workflow_escalated=workflow_result.escalated,
        workflow_correct=workflow_result.escalated == scenario.should_escalate,
        agent_escalated=agent_result.escalated,
        agent_correct=agent_result.escalated == scenario.should_escalate,
        agent_confidence=agent_result.overall_confidence,
    )


def compute_aggregate(comparisons: list[ScenarioComparison]) -> AggregateMetrics:
    """전체 비교 결과에서 집계 메트릭을 산출."""
    total = len(comparisons)

    w_correct = sum(1 for c in comparisons if c.workflow_correct)
    w_fp = sum(
        1 for c in comparisons
        if c.workflow_escalated and not c.ground_truth_escalate
    )
    w_fn = sum(
        1 for c in comparisons
        if not c.workflow_escalated and c.ground_truth_escalate
    )

    a_correct = sum(1 for c in comparisons if c.agent_correct)
    a_fp = sum(
        1 for c in comparisons
        if c.agent_escalated and not c.ground_truth_escalate
    )
    a_fn = sum(
        1 for c in comparisons
        if not c.agent_escalated and c.ground_truth_escalate
    )

    w_acc = w_correct / total if total else 0
    a_acc = a_correct / total if total else 0

    return AggregateMetrics(
        total=total,
        workflow_correct=w_correct,
        workflow_accuracy=round(w_acc, 2),
        workflow_false_positives=w_fp,
        workflow_false_negatives=w_fn,
        workflow_fp_rate=round(w_fp / total, 2) if total else 0,
        workflow_fn_rate=round(w_fn / total, 2) if total else 0,
        agent_correct=a_correct,
        agent_accuracy=round(a_acc, 2),
        agent_false_positives=a_fp,
        agent_false_negatives=a_fn,
        agent_fp_rate=round(a_fp / total, 2) if total else 0,
        agent_fn_rate=round(a_fn / total, 2) if total else 0,
        accuracy_delta=round(a_acc - w_acc, 2),
    )
