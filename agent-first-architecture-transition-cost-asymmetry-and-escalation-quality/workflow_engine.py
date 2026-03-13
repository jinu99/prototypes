"""
Workflow 엔진: 하드코딩된 규칙 기반 분기로 에스컬레이션을 결정한다.
전형적인 if/else 기반 고객 지원 시스템의 한계를 보여주는 구현.
"""

from dataclasses import dataclass, field, asdict
from scenarios import Scenario


@dataclass
class WorkflowStep:
    name: str
    rule_applied: str
    result: str


@dataclass
class WorkflowResult:
    scenario_id: str
    escalated: bool
    escalation_target: str  # "none", "level2", "manager", "security"
    steps: list[WorkflowStep] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self):
        d = asdict(self)
        return d


# 하드코딩된 에스컬레이션 규칙
KEYWORD_ESCALATION = {
    "환불": "level2",
    "해지": "manager",
    "취소": "level2",
    "소송": "manager",
    "법적": "manager",
    "관리자": "manager",
    "비밀번호": None,  # 자동 처리
}

CATEGORY_ROUTING = {
    "billing": "billing_team",
    "technical": "tech_team",
    "complaint": "manager",
    "account": "account_team",
    "general": "general_team",
}


def process_workflow(scenario: Scenario) -> WorkflowResult:
    """규칙 기반 Workflow로 시나리오를 처리한다."""
    steps: list[WorkflowStep] = []
    escalated = False
    escalation_target = "none"

    # Step 1: 카테고리 라우팅
    route = CATEGORY_ROUTING.get(scenario.category, "general_team")
    steps.append(WorkflowStep(
        name="카테고리 라우팅",
        rule_applied=f"category == '{scenario.category}' → {route}",
        result=f"{route}으로 라우팅",
    ))

    # Step 2: 키워드 스캔
    msg = scenario.customer_message
    matched_keywords = []
    for keyword, target in KEYWORD_ESCALATION.items():
        if keyword in msg:
            matched_keywords.append((keyword, target))

    if matched_keywords:
        keyword_desc = ", ".join(f"'{k}'" for k, _ in matched_keywords)
        steps.append(WorkflowStep(
            name="키워드 매칭",
            rule_applied=f"메시지에서 키워드 발견: {keyword_desc}",
            result="키워드 기반 에스컬레이션 판단",
        ))
        # 가장 높은 에스컬레이션 레벨 선택
        for _, target in matched_keywords:
            if target == "manager":
                escalation_target = "manager"
                escalated = True
            elif target == "level2" and escalation_target != "manager":
                escalation_target = "level2"
                escalated = True
    else:
        steps.append(WorkflowStep(
            name="키워드 매칭",
            rule_applied="에스컬레이션 키워드 없음",
            result="에스컬레이션 불필요 판단",
        ))

    # Step 3: 감정 키워드 체크 (매우 단순한 규칙)
    anger_keywords = ["화가", "짜증", "최악", "실망", "분노"]
    anger_found = [k for k in anger_keywords if k in msg]
    if anger_found:
        steps.append(WorkflowStep(
            name="감정 키워드 체크",
            rule_applied=f"감정 키워드 발견: {anger_found}",
            result="매니저 에스컬레이션",
        ))
        escalated = True
        escalation_target = "manager"
    else:
        steps.append(WorkflowStep(
            name="감정 키워드 체크",
            rule_applied="감정 키워드 없음",
            result="에스컬레이션 불필요",
        ))

    # Step 4: 결정
    reasoning_parts = []
    if escalated:
        reasoning_parts.append(f"규칙에 의해 {escalation_target}으로 에스컬레이션")
    else:
        reasoning_parts.append("규칙 기반 자동 처리")

    steps.append(WorkflowStep(
        name="최종 결정",
        rule_applied="규칙 기반 분기 완료",
        result=f"에스컬레이션={'예' if escalated else '아니오'}, "
               f"대상={escalation_target}",
    ))

    return WorkflowResult(
        scenario_id=scenario.id,
        escalated=escalated,
        escalation_target=escalation_target,
        steps=steps,
        reasoning=" / ".join(reasoning_parts),
    )
