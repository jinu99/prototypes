"""
Agent 엔진: 5가지 판단 순간에서 confidence 기반으로 에스컬레이션을 결정한다.
각 판단 순간마다 시나리오의 속성(ambiguity, emotional_intensity 등)을 기반으로
confidence 점수를 계산하고, 임계값 이하이면 에스컬레이션을 고려한다.

5가지 판단 순간:
  1. Intent 해석 — 고객의 의도를 얼마나 확신하는가
  2. Tool 선택 — 어떤 도구/액션을 써야 하는지 확신하는가
  3. Context 충분성 — 판단에 필요한 맥락이 충분한가
  4. 결과 검증 — 내 액션이 문제를 해결했는가
  5. 사람 개입 판단 — 종합적으로 사람이 필요한가
"""

from dataclasses import dataclass, field, asdict
from scenarios import Scenario

DEFAULT_CONFIDENCE_THRESHOLD = 0.65  # 기본 임계값
CONFIDENCE_THRESHOLD = DEFAULT_CONFIDENCE_THRESHOLD


@dataclass
class DecisionMoment:
    """5가지 판단 순간 중 하나의 결과."""
    name: str
    confidence: float  # 0~1
    factors: list[str]  # confidence 계산에 사용된 요소들
    decision: str  # "proceed", "flag", "escalate"

    @property
    def passed(self) -> bool:
        return self.decision == "proceed"


@dataclass
class AgentResult:
    scenario_id: str
    escalated: bool
    escalation_target: str
    decision_moments: list[DecisionMoment] = field(default_factory=list)
    overall_confidence: float = 0.0
    reasoning: str = ""

    def to_dict(self):
        d = asdict(self)
        return d


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _assess_intent(scenario: Scenario) -> DecisionMoment:
    """판단 순간 1: Intent 해석 — 고객이 무엇을 원하는지 파악."""
    factors = []
    confidence = 1.0

    # 애매함이 높을수록 intent 파악이 어려움
    confidence -= scenario.ambiguity * 0.5
    if scenario.ambiguity > 0.5:
        factors.append(f"높은 애매함({scenario.ambiguity:.1f}): 의도 불명확")

    # 여러 카테고리에 걸친 문제
    if scenario.multi_category:
        confidence -= 0.25
        factors.append("다중 카테고리 문제: 단일 의도 파악 어려움")

    # 감정이 강하면 실제 의도가 감정에 묻힐 수 있음
    if scenario.emotional_intensity > 0.6:
        confidence -= 0.15
        factors.append(f"감정 강도({scenario.emotional_intensity:.1f}): 실제 의도 파악 방해")

    if not factors:
        factors.append("명확한 단일 의도 파악 가능")

    confidence = _clamp(confidence)
    decision = "proceed" if confidence >= CONFIDENCE_THRESHOLD else "flag"

    return DecisionMoment(
        name="Intent 해석",
        confidence=round(confidence, 2),
        factors=factors,
        decision=decision,
    )


def _assess_tool_selection(scenario: Scenario) -> DecisionMoment:
    """판단 순간 2: Tool 선택 — 어떤 도구/액션을 써야 하는지."""
    factors = []
    confidence = 1.0

    # 다중 카테고리면 어떤 팀의 도구를 써야 할지 불명확
    if scenario.multi_category:
        confidence -= 0.35
        factors.append("다중 카테고리: 어떤 도구 세트를 쓸지 불확실")

    # 판단이 필요한 경우 자동화 도구로 해결 불가
    if scenario.requires_judgment:
        confidence -= 0.2
        factors.append("맥락적 판단 필요: 자동화 도구 부족")

    # context에 해결 정보가 있으면 confidence 상승
    ctx = scenario.context
    if ctx.get("known_issue") or ctx.get("fix"):
        confidence += 0.1
        factors.append("알려진 이슈/해결책 존재")
    if ctx.get("refund_authority_needed"):
        confidence -= 0.3
        factors.append("환불 권한 필요: 자동 처리 불가")
    if ctx.get("admin_access_requested"):
        confidence -= 0.4
        factors.append("관리자 접근 요청: 보안 프로토콜 필요")
    if ctx.get("current_outage"):
        confidence -= 0.3
        factors.append("서비스 장애 중: 일반 도구로 대응 불가")

    if not factors:
        factors.append("표준 도구로 처리 가능")

    confidence = _clamp(confidence)
    decision = "proceed" if confidence >= CONFIDENCE_THRESHOLD else "flag"

    return DecisionMoment(
        name="Tool 선택",
        confidence=round(confidence, 2),
        factors=factors,
        decision=decision,
    )


def _assess_context_sufficiency(scenario: Scenario) -> DecisionMoment:
    """판단 순간 3: Context 충분성 — 판단에 필요한 정보가 있는지."""
    factors = []
    confidence = 1.0

    ctx = scenario.context

    # 신원 확인 여부
    if ctx.get("caller_verified") is False:
        confidence -= 0.4
        factors.append("신원 미확인: 정보 제공 위험")
    elif ctx.get("account_verified"):
        factors.append("계정 확인 완료")

    # 이메일 도메인 불일치
    if ctx.get("email_domain_mismatch"):
        confidence -= 0.35
        factors.append("이메일 도메인 불일치: 피싱 의심")

    # 이전 문의 이력
    prev_contacts = ctx.get("previous_contacts", 0)
    if prev_contacts >= 3:
        confidence -= 0.2
        factors.append(f"반복 문의({prev_contacts}회): 이전 처리 맥락 필요")

    # 이탈 위험 신호
    churn_signals = ctx.get("churn_risk_signals", [])
    if churn_signals:
        confidence -= 0.15 * len(churn_signals)
        factors.append(f"이탈 위험 신호 {len(churn_signals)}개: {churn_signals}")

    # SLA 관련
    if ctx.get("sla_response_hours"):
        confidence -= 0.15
        factors.append(f"SLA 보장({ctx['sla_response_hours']}시간): 긴급 프로토콜 필요")

    # 대규모 영향
    affected = ctx.get("affected_users", 0)
    if affected >= 50:
        confidence -= 0.2
        factors.append(f"영향 범위 {affected}명: 대규모 장애 대응 필요")

    if not factors:
        factors.append("충분한 맥락 확보")

    confidence = _clamp(confidence)
    decision = "proceed" if confidence >= CONFIDENCE_THRESHOLD else "flag"

    return DecisionMoment(
        name="Context 충분성",
        confidence=round(confidence, 2),
        factors=factors,
        decision=decision,
    )


def _assess_result_verification(
    scenario: Scenario, prev_moments: list[DecisionMoment]
) -> DecisionMoment:
    """판단 순간 4: 결과 검증 — 이전 판단들의 결과를 종합 검증."""
    factors = []

    # 이전 판단 순간들의 평균 confidence
    avg_conf = sum(m.confidence for m in prev_moments) / len(prev_moments)
    flagged_count = sum(1 for m in prev_moments if m.decision == "flag")

    confidence = avg_conf

    if flagged_count >= 2:
        confidence -= 0.2
        factors.append(f"이전 단계에서 {flagged_count}개 플래그: 누적 불확실성 높음")
    elif flagged_count == 1:
        confidence -= 0.1
        factors.append("이전 단계에서 1개 플래그: 부분적 불확실성")
    else:
        factors.append("이전 단계 모두 통과")

    # 복합 케이스인데 단순 처리하면 결과 검증 실패
    if scenario.complexity in ("complex", "edge") and avg_conf > 0.8:
        # 복합 문제를 너무 쉽게 넘긴 것 — 의심
        confidence -= 0.1
        factors.append("복합 시나리오인데 높은 confidence: 과신 가능성")

    if not factors:
        factors.append("결과 검증 통과")

    confidence = _clamp(confidence)
    decision = "proceed" if confidence >= CONFIDENCE_THRESHOLD else "flag"

    return DecisionMoment(
        name="결과 검증",
        confidence=round(confidence, 2),
        factors=factors,
        decision=decision,
    )


def _assess_human_intervention(
    scenario: Scenario, prev_moments: list[DecisionMoment]
) -> DecisionMoment:
    """판단 순간 5: 사람 개입 판단 — 종합적으로 사람이 필요한지."""
    factors = []
    confidence = 1.0

    # 이전 판단의 종합 평가
    flagged = [m for m in prev_moments if m.decision == "flag"]
    avg_conf = sum(m.confidence for m in prev_moments) / len(prev_moments)

    if len(flagged) >= 3:
        confidence = 0.2
        factors.append(f"3개 이상 단계 플래그: 사람 개입 강력 권고")
    elif len(flagged) >= 2:
        confidence = 0.4
        factors.append(f"2개 단계 플래그: 사람 개입 권고")
    elif len(flagged) == 1:
        confidence = 0.7
        factors.append("1개 단계 플래그: 주의 필요")
    else:
        confidence = 0.9
        factors.append("모든 단계 통과: 자동 처리 가능")

    # 감정 강도가 높으면 사람의 공감 필요
    if scenario.emotional_intensity > 0.7:
        confidence -= 0.15
        factors.append("높은 감정 강도: 사람의 공감 필요")

    # 보안 관련 맥락
    ctx = scenario.context
    if ctx.get("admin_access_requested") or ctx.get("email_domain_mismatch"):
        confidence -= 0.3
        factors.append("보안 관련 사안: 보안팀 검토 필요")

    confidence = _clamp(confidence)
    decision = "proceed" if confidence >= CONFIDENCE_THRESHOLD else "escalate"

    return DecisionMoment(
        name="사람 개입 판단",
        confidence=round(confidence, 2),
        factors=factors,
        decision=decision,
    )


def _determine_target(scenario: Scenario, moments: list[DecisionMoment]) -> str:
    """에스컬레이션 대상을 결정한다."""
    ctx = scenario.context
    if ctx.get("admin_access_requested") or ctx.get("email_domain_mismatch"):
        return "security"
    if ctx.get("sla_response_hours") or ctx.get("current_outage"):
        return "senior_engineer"
    if ctx.get("churn_risk_signals"):
        return "retention_team"
    if ctx.get("refund_authority_needed"):
        return "manager"
    if scenario.multi_category:
        return "specialist"
    return "level2"


def process_agent(scenario: Scenario, threshold: float | None = None) -> AgentResult:
    """Agent 엔진으로 시나리오를 처리한다. 5가지 판단 순간을 순차 평가."""
    global CONFIDENCE_THRESHOLD
    old_threshold = CONFIDENCE_THRESHOLD
    if threshold is not None:
        CONFIDENCE_THRESHOLD = threshold

    moments: list[DecisionMoment] = []

    # 순차적으로 5가지 판단 순간 평가
    m1 = _assess_intent(scenario)
    moments.append(m1)

    m2 = _assess_tool_selection(scenario)
    moments.append(m2)

    m3 = _assess_context_sufficiency(scenario)
    moments.append(m3)

    m4 = _assess_result_verification(scenario, moments[:3])
    moments.append(m4)

    m5 = _assess_human_intervention(scenario, moments[:4])
    moments.append(m5)

    CONFIDENCE_THRESHOLD = old_threshold

    # 종합 판단
    overall_confidence = sum(m.confidence for m in moments) / len(moments)
    escalated = m5.decision == "escalate"
    escalation_target = _determine_target(scenario, moments) if escalated else "none"

    # 추론 과정 요약
    reasoning_parts = []
    for m in moments:
        status = "✓" if m.decision == "proceed" else "⚠" if m.decision == "flag" else "✕"
        reasoning_parts.append(f"{status} {m.name}({m.confidence:.0%})")
    reasoning = " → ".join(reasoning_parts)

    return AgentResult(
        scenario_id=scenario.id,
        escalated=escalated,
        escalation_target=escalation_target,
        decision_moments=moments,
        overall_confidence=round(overall_confidence, 2),
        reasoning=reasoning,
    )
