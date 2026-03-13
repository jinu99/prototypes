"""Multi-turn stability probe: detect context collapse and repetition."""

from __future__ import annotations

import re
from dataclasses import dataclass

from llm_qual_probe.client import LLMClient


CONVERSATION_SEEDS = [
    {
        "topic": "travel_planning",
        "turns": [
            "I'm planning a trip to Japan next month. What cities should I visit?",
            "I'll spend 3 days in Tokyo. What neighborhoods should I explore?",
            "What about food? What are the must-try dishes in Tokyo?",
            "Now let's talk about Kyoto. What temples should I visit?",
            "Can you summarize the complete itinerary we've discussed so far?",
            "What was the first city I mentioned wanting to visit?",
            "How many days did I say I'd spend in Tokyo?",
        ],
    },
    {
        "topic": "code_review",
        "turns": [
            "I have a Python function that sorts a list using bubble sort. Can you review it?",
            "What's the time complexity of bubble sort?",
            "Can you suggest a more efficient sorting algorithm?",
            "Write a merge sort implementation in Python.",
            "Compare the two algorithms we discussed: bubble sort and merge sort.",
            "What was the first algorithm I asked you about?",
            "What language did I ask you to write the merge sort in?",
        ],
    },
]


@dataclass
class TurnResult:
    turn_number: int
    user_message: str
    assistant_response: str
    tokens_used: int
    repetition_detected: bool
    context_forgotten: bool
    issues: list[str]


def _detect_repetition(current: str, previous: list[str]) -> bool:
    if not previous:
        return False
    current_clean = re.sub(r'\s+', ' ', current.strip().lower())
    for prev in previous[-3:]:
        prev_clean = re.sub(r'\s+', ' ', prev.strip().lower())
        if len(current_clean) > 20 and len(prev_clean) > 20:
            # Check for high similarity via shared long substrings
            words_cur = current_clean.split()
            words_prev = prev_clean.split()
            if len(words_cur) > 5 and len(words_prev) > 5:
                overlap = set(words_cur) & set(words_prev)
                ratio = len(overlap) / max(len(set(words_cur)), len(set(words_prev)))
                if ratio > 0.85:
                    return True
    # Self-repetition within the same response
    sentences = re.split(r'[.!?]+', current)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 10]
    if len(sentences) > 2:
        unique = set(sentences)
        if len(unique) < len(sentences) * 0.5:
            return True
    return False


def _detect_context_loss(response: str, turn_number: int, topic_data: dict) -> bool:
    """Check if model forgot earlier context on recall turns (turn >= 5)."""
    if turn_number < 5:
        return False
    response_lower = response.lower()
    topic = topic_data["topic"]
    if topic == "travel_planning":
        if turn_number == 5:
            return "japan" not in response_lower and "tokyo" not in response_lower and "kyoto" not in response_lower
        if turn_number == 6:
            return "japan" not in response_lower
        if turn_number == 7:
            return "3" not in response and "three" not in response_lower
    elif topic == "code_review":
        if turn_number == 5:
            return "bubble" not in response_lower and "merge" not in response_lower
        if turn_number == 6:
            return "bubble" not in response_lower
        if turn_number == 7:
            return "python" not in response_lower
    return False


def run_conversation(client: LLMClient, seed: dict, max_turns: int = 7) -> list[TurnResult]:
    messages = [{"role": "system", "content": "You are a helpful assistant. Remember all details from the conversation."}]
    results = []
    prev_responses = []

    turns = seed["turns"][:max_turns]
    for i, user_msg in enumerate(turns):
        messages.append({"role": "user", "content": user_msg})
        resp = client.chat(messages, temperature=0.5, max_tokens=512)
        messages.append({"role": "assistant", "content": resp.content})

        rep = _detect_repetition(resp.content, prev_responses)
        ctx_lost = _detect_context_loss(resp.content, i + 1, seed)

        issues = []
        if rep:
            issues.append("repetition_detected")
        if ctx_lost:
            issues.append("context_forgotten")

        results.append(TurnResult(
            turn_number=i + 1,
            user_message=user_msg,
            assistant_response=resp.content,
            tokens_used=resp.total_tokens,
            repetition_detected=rep,
            context_forgotten=ctx_lost,
            issues=issues,
        ))
        prev_responses.append(resp.content)

    return results


def run(client: LLMClient) -> dict:
    all_conversations = []
    collapse_points = []

    for seed in CONVERSATION_SEEDS:
        turn_results = run_conversation(client, seed)
        conv_data = {
            "topic": seed["topic"],
            "turns": [
                {
                    "turn": t.turn_number,
                    "user": t.user_message[:80],
                    "response": t.assistant_response[:200],
                    "tokens": t.tokens_used,
                    "repetition": t.repetition_detected,
                    "context_forgotten": t.context_forgotten,
                    "issues": t.issues,
                }
                for t in turn_results
            ],
        }
        all_conversations.append(conv_data)

        for t in turn_results:
            if t.issues:
                collapse_points.append({
                    "topic": seed["topic"],
                    "turn": t.turn_number,
                    "issues": t.issues,
                })

    total_turns = sum(len(c["turns"]) for c in all_conversations)
    failed_turns = len(collapse_points)
    stability_rate = (total_turns - failed_turns) / total_turns if total_turns else 0

    if stability_rate >= 0.85:
        status = "PASS"
    elif stability_rate >= 0.6:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "probe": "multiturn_stability",
        "status": status,
        "summary": {
            "total_turns": total_turns,
            "stable_turns": total_turns - failed_turns,
            "stability_rate": round(stability_rate * 100, 1),
            "collapse_points": collapse_points,
        },
        "details": all_conversations,
    }
