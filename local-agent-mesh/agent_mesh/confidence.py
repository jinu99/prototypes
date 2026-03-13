"""Self-evaluation and confidence assessment.

After a small model generates a response, this module evaluates
the response quality and decides whether to escalate to a larger model.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_mesh.models import ModelResponse, generate


# Confidence threshold — below this, escalate to large model
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ConfidenceResult:
    score: float  # 0.0 = no confidence, 1.0 = fully confident
    should_escalate: bool
    reasons: list[str]
    method: str  # "self_eval" or "heuristic"


def evaluate_confidence(
    prompt: str,
    response: ModelResponse,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ConfidenceResult:
    """Evaluate confidence in a model's response.

    Uses a hybrid approach:
    1. Heuristic signals (hedging language, incompleteness, length)
    2. Self-evaluation prompt (asks the model to rate itself)

    In mock mode, uses heuristics only. With real Ollama, also
    uses self-evaluation prompts.
    """
    reasons = []
    scores = []

    # --- Heuristic signals ---
    text = response.text.lower()

    # Hedging / uncertainty language
    hedging_phrases = [
        "i'm not sure", "i'm not confident", "not fully confident",
        "i think", "might be", "might need", "perhaps",
        "uncertain", "not certain", "incomplete",
        "need more", "잘 모르겠", "확실하지 않",
    ]
    hedge_count = sum(1 for phrase in hedging_phrases if phrase in text)
    if hedge_count > 0:
        hedge_penalty = min(0.3, hedge_count * 0.1)
        scores.append(1.0 - hedge_penalty)
        reasons.append(f"Hedging language detected ({hedge_count} phrases, -{hedge_penalty:.1f})")
    else:
        scores.append(1.0)
        reasons.append("No hedging language")

    # Response length relative to prompt complexity
    prompt_words = len(prompt.split())
    response_words = len(response.text.split())
    if prompt_words > 20 and response_words < 30:
        scores.append(0.4)
        reasons.append(f"Short response ({response_words}w) for complex prompt ({prompt_words}w)")
    elif response_words > 20:
        scores.append(0.85)
        reasons.append(f"Adequate response length ({response_words} words)")
    else:
        scores.append(0.7)
        reasons.append(f"Response length: {response_words} words")

    # Completeness signals
    incomplete_markers = ["...", "(incomplete", "todo", "to be continued"]
    has_incomplete = any(marker in text for marker in incomplete_markers)
    if has_incomplete:
        scores.append(0.3)
        reasons.append("Incomplete markers detected")
    else:
        scores.append(0.9)
        reasons.append("No incompleteness markers")

    # Structured output quality (for code tasks)
    if "```" in response.text:
        code_blocks = response.text.count("```") // 2
        if code_blocks >= 1:
            scores.append(0.8)
            reasons.append(f"Contains {code_blocks} code block(s)")
        else:
            scores.append(0.5)
            reasons.append("Malformed code block")

    # Self-evaluation via prompt (only with real Ollama)
    method = "heuristic"
    if not response.is_mock:
        self_eval = _self_evaluate_via_prompt(prompt, response)
        scores.append(self_eval.score)
        reasons.extend(self_eval.reasons)
        method = "self_eval + heuristic"

    # Aggregate scores
    final_score = sum(scores) / len(scores)
    should_escalate = final_score < threshold

    reasons.append(f"Aggregate confidence: {final_score:.2f} (threshold: {threshold})")
    if should_escalate:
        reasons.append("→ ESCALATE to large model")
    else:
        reasons.append("→ ACCEPT response")

    return ConfidenceResult(
        score=final_score,
        should_escalate=should_escalate,
        reasons=reasons,
        method=method,
    )


def _self_evaluate_via_prompt(
    original_prompt: str,
    response: ModelResponse,
) -> ConfidenceResult:
    """Ask the model to self-evaluate its response quality."""
    eval_prompt = (
        f"You are evaluating the quality of an AI response.\n\n"
        f"Original question: {original_prompt}\n\n"
        f"Response to evaluate:\n{response.text}\n\n"
        f"Rate the response quality on a scale of 0.0 to 1.0 where:\n"
        f"- 0.0-0.3: Poor, incomplete, or incorrect\n"
        f"- 0.4-0.6: Partial, missing important details\n"
        f"- 0.7-0.8: Good but could be improved\n"
        f"- 0.9-1.0: Excellent, comprehensive, and accurate\n\n"
        f"Respond with ONLY a number between 0.0 and 1.0."
    )

    eval_response = generate(response.model, eval_prompt)

    try:
        score = float(eval_response.text.strip())
        score = max(0.0, min(1.0, score))
        return ConfidenceResult(
            score=score,
            should_escalate=False,  # caller will decide
            reasons=[f"Self-eval score: {score:.2f}"],
            method="self_eval",
        )
    except ValueError:
        return ConfidenceResult(
            score=0.5,
            should_escalate=False,
            reasons=["Self-eval parse failed, defaulting to 0.5"],
            method="self_eval",
        )
