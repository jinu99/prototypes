"""
에스컬레이션 품질 시뮬레이터 CLI.
Workflow vs Agent 엔진으로 시나리오를 처리하고 결과를 비교한다.
"""

import json
from pathlib import Path

from scenarios import SCENARIOS
from workflow_engine import process_workflow
from agent_engine import process_agent
from comparator import compare_single, compute_aggregate


OUTPUT_DIR = Path(__file__).parent / "output"


def run_simulation():
    """모든 시나리오에 대해 Workflow/Agent 시뮬레이션을 실행한다."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    workflow_results = []
    agent_results = []
    comparisons = []

    print("=" * 70)
    print("  에스컬레이션 품질 시뮬레이터: Workflow vs Agent")
    print("=" * 70)
    print()

    for scenario in SCENARIOS:
        w_result = process_workflow(scenario)
        a_result = process_agent(scenario)
        comparison = compare_single(scenario, w_result, a_result)

        workflow_results.append(w_result)
        agent_results.append(a_result)
        comparisons.append(comparison)

        _print_scenario_result(scenario, w_result, a_result, comparison)

    # 집계
    metrics = compute_aggregate(comparisons)
    _print_aggregate(metrics)

    # 결과 저장 (대시보드용)
    output_data = {
        "scenarios": [s.to_dict() for s in SCENARIOS],
        "workflow_results": [r.to_dict() for r in workflow_results],
        "agent_results": [r.to_dict() for r in agent_results],
        "comparisons": [c.to_dict() for c in comparisons],
        "metrics": metrics.to_dict(),
    }
    # 임계값 민감도 분석
    sensitivity = _run_sensitivity_analysis()
    output_data["sensitivity"] = sensitivity
    _print_sensitivity(sensitivity)

    output_path = OUTPUT_DIR / "results.json"
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {output_path}")
    print(f"대시보드: uv run server.py 실행 후 http://localhost:8000 접속")


def _print_scenario_result(scenario, w_result, a_result, comparison):
    """개별 시나리오 결과를 출력한다."""
    complexity_badge = {"simple": "○", "complex": "◉", "edge": "◆"}
    badge = complexity_badge.get(scenario.complexity, "?")

    print(f"─── {badge} [{scenario.id}] {scenario.title} ({scenario.complexity}) ───")
    print(f"  메시지: {scenario.customer_message[:60]}...")

    # Ground truth
    gt = "에스컬레이션 필요" if scenario.should_escalate else "자동 처리 가능"
    print(f"  정답: {gt}", end="")
    if scenario.escalation_reason:
        print(f" ({scenario.escalation_reason})")
    else:
        print()

    # Workflow 결과
    w_mark = "✓" if comparison.workflow_correct else "✗"
    w_esc = "에스컬레이션" if w_result.escalated else "자동 처리"
    print(f"  Workflow: {w_mark} {w_esc} → {w_result.escalation_target}")

    # Agent 결과
    a_mark = "✓" if comparison.agent_correct else "✗"
    a_esc = "에스컬레이션" if a_result.escalated else "자동 처리"
    print(f"  Agent:    {a_mark} {a_esc} → {a_result.escalation_target} "
          f"(confidence: {a_result.overall_confidence:.0%})")
    print(f"            {a_result.reasoning}")
    print()


def _print_aggregate(metrics):
    """집계 메트릭을 출력한다."""
    print("=" * 70)
    print("  집계 결과")
    print("=" * 70)
    print()
    print(f"  총 시나리오: {metrics.total}")
    print()
    print(f"  {'':20s} {'Workflow':>10s} {'Agent':>10s} {'차이':>10s}")
    print(f"  {'─' * 52}")
    print(f"  {'정확도':20s} {metrics.workflow_accuracy:>9.0%} "
          f"{metrics.agent_accuracy:>9.0%} "
          f"{_delta_str(metrics.accuracy_delta)}")
    print(f"  {'불필요 에스컬레이션':20s} {metrics.workflow_false_positives:>10d} "
          f"{metrics.agent_false_positives:>10d}")
    print(f"  {'놓친 에스컬레이션':20s} {metrics.workflow_false_negatives:>10d} "
          f"{metrics.agent_false_negatives:>10d}")
    print()

    if metrics.accuracy_delta > 0:
        print(f"  → Agent가 Workflow보다 {metrics.accuracy_delta:.0%}p 더 정확합니다.")
    elif metrics.accuracy_delta == 0:
        print(f"  → 두 엔진의 정확도가 동일합니다.")
    else:
        print(f"  → Workflow가 Agent보다 {-metrics.accuracy_delta:.0%}p 더 정확합니다.")

    if metrics.workflow_false_negatives > metrics.agent_false_negatives:
        diff = metrics.workflow_false_negatives - metrics.agent_false_negatives
        print(f"  → Agent는 Workflow가 놓친 {diff}개의 에스컬레이션을 포착했습니다.")


def _run_sensitivity_analysis() -> list[dict]:
    """다양한 confidence 임계값에서 Agent 정확도를 측정한다."""
    thresholds = [0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9]
    results = []

    for t in thresholds:
        correct = 0
        fp = 0
        fn = 0
        for scenario in SCENARIOS:
            a_result = process_agent(scenario, threshold=t)
            if a_result.escalated == scenario.should_escalate:
                correct += 1
            if a_result.escalated and not scenario.should_escalate:
                fp += 1
            if not a_result.escalated and scenario.should_escalate:
                fn += 1
        results.append({
            "threshold": t,
            "accuracy": round(correct / len(SCENARIOS), 2),
            "false_positives": fp,
            "false_negatives": fn,
        })

    return results


def _print_sensitivity(sensitivity: list[dict]):
    """임계값 민감도 분석 결과를 출력한다."""
    print()
    print("=" * 70)
    print("  임계값 민감도 분석 (Agent)")
    print("=" * 70)
    print()
    print(f"  {'임계값':>8s}  {'정확도':>8s}  {'놓침':>6s}  {'과잉':>6s}  {'평가':>10s}")
    print(f"  {'─' * 48}")

    for row in sensitivity:
        t = row["threshold"]
        acc = row["accuracy"]
        fn = row["false_negatives"]
        fp = row["false_positives"]

        # 평가: 정확도, FP/FN 균형
        if acc >= 1.0 and fp == 0 and fn == 0:
            grade = "최적"
        elif acc >= 0.9:
            grade = "양호"
        elif acc >= 0.7:
            grade = "보통"
        else:
            grade = "부적합"

        bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
        print(f"  {t:>8.2f}  {acc:>7.0%}  {fn:>6d}  {fp:>6d}  {grade:>10s}  {bar}")

    print()
    best = max(sensitivity, key=lambda r: r["accuracy"])
    print(f"  → 최적 임계값: {best['threshold']} (정확도 {best['accuracy']:.0%})")


def _delta_str(delta: float) -> str:
    if delta > 0:
        return f"+{delta:.0%}p"
    elif delta < 0:
        return f"{delta:.0%}p"
    return "  0%p"


if __name__ == "__main__":
    run_simulation()
