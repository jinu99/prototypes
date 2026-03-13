"""Output efficiency probe: compare token usage with thinking on/off and system prompt variants."""

from __future__ import annotations

from llm_qual_probe.client import LLMClient


TEST_PROMPTS = [
    "What is the capital of France? Answer in one sentence.",
    "Explain what a hash table is in 2-3 sentences.",
    "List 3 benefits of exercise. Be concise.",
]

SYSTEM_VARIANTS = {
    "minimal": "Answer concisely.",
    "detailed": "You are a helpful assistant. Provide thorough, detailed answers with examples.",
    "structured": "You are a helpful assistant. Always respond in a structured format with headers.",
}


def _run_with_config(
    client: LLMClient,
    prompts: list[str],
    system_prompt: str,
    label: str,
) -> dict:
    results = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for prompt in prompts:
        resp = client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        total_prompt_tokens += resp.prompt_tokens
        total_completion_tokens += resp.completion_tokens
        results.append({
            "prompt": prompt,
            "response_length": len(resp.content),
            "prompt_tokens": resp.prompt_tokens,
            "completion_tokens": resp.completion_tokens,
            "total_tokens": resp.total_tokens,
        })

    return {
        "config": label,
        "system_prompt": system_prompt[:80],
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "avg_completion_tokens": round(total_completion_tokens / len(prompts), 1) if prompts else 0,
        "details": results,
    }


def run(client: LLMClient) -> dict:
    configs = []

    # Test with thinking-style system prompt (simulated "thinking on")
    thinking_on = _run_with_config(
        client,
        TEST_PROMPTS,
        "Think step by step before answering. Show your reasoning process.",
        "thinking_on",
    )
    configs.append(thinking_on)

    # Test with direct answer (simulated "thinking off")
    thinking_off = _run_with_config(
        client,
        TEST_PROMPTS,
        "Answer directly and concisely. No reasoning or explanation needed.",
        "thinking_off",
    )
    configs.append(thinking_off)

    # Test system prompt variants
    for label, sys_prompt in SYSTEM_VARIANTS.items():
        result = _run_with_config(client, TEST_PROMPTS, sys_prompt, f"system_{label}")
        configs.append(result)

    # Compare thinking on vs off
    on_tokens = thinking_on["total_completion_tokens"]
    off_tokens = thinking_off["total_completion_tokens"]
    if off_tokens > 0:
        thinking_overhead = round((on_tokens - off_tokens) / off_tokens * 100, 1)
    else:
        thinking_overhead = 0.0

    # Find most/least efficient system prompt
    all_completion = [(c["config"], c["avg_completion_tokens"]) for c in configs]
    all_completion.sort(key=lambda x: x[1])

    if on_tokens > off_tokens * 2:
        status = "WARN"
    elif on_tokens > off_tokens * 3:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "probe": "output_efficiency",
        "status": status,
        "summary": {
            "thinking_on_tokens": on_tokens,
            "thinking_off_tokens": off_tokens,
            "thinking_overhead_pct": thinking_overhead,
            "most_efficient": all_completion[0][0] if all_completion else "",
            "least_efficient": all_completion[-1][0] if all_completion else "",
        },
        "configs": configs,
    }
