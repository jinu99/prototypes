"""LLM client wrapper for OpenAI-compatible APIs."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""


@dataclass
class LLMClient:
    base_url: str
    model: str = ""
    mock: bool = False

    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self):
        api_url = self.base_url.rstrip("/")
        if not api_url.endswith("/v1"):
            api_url += "/v1"
        self._client = OpenAI(base_url=api_url, api_key="not-needed")

    def detect_model(self) -> str:
        if self.mock:
            self.model = "mock-model"
            return self.model
        models = self._client.models.list()
        if models.data:
            self.model = models.data[0].id
        return self.model

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if self.mock:
            return self._mock_response(messages)

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            content=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=resp.model,
        )

    _mock_turn: int = field(init=False, default=0, repr=False)

    def _mock_response(self, messages: list[dict[str, str]]) -> LLMResponse:
        last = messages[-1]["content"] if messages else ""
        sys_prompt = ""
        for m in messages:
            if m["role"] == "system":
                sys_prompt = m["content"]
                break

        if "json" in last.lower() or "JSON" in last:
            return self._mock_json_response(last)
        if "yaml" in last.lower() or "YAML" in last:
            return self._mock_yaml_response(last)

        # Check for thinking/efficiency probes — vary token count by system prompt
        is_thinking = "step by step" in sys_prompt.lower() or "show your reasoning" in sys_prompt.lower()

        # Contextual mock responses for multi-turn
        self._mock_turn += 1
        content = self._mock_conversational(last, messages, is_thinking)
        prompt_tokens = sum(len(m["content"].split()) for m in messages)
        comp_tokens = len(content.split())
        if is_thinking:
            comp_tokens = int(comp_tokens * 1.8)  # simulate thinking overhead
        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            total_tokens=prompt_tokens + comp_tokens,
            model="mock-model",
        )

    def _mock_conversational(self, last: str, messages: list[dict[str, str]], verbose: bool) -> str:
        last_lower = last.lower()

        # Travel-related context-aware responses
        if "japan" in last_lower and "cities" in last_lower:
            return "For Japan, I recommend visiting Tokyo, Kyoto, and Osaka. Tokyo for modern culture, Kyoto for temples, and Osaka for street food."
        if "tokyo" in last_lower and "neighborhood" in last_lower:
            return "In Tokyo, explore Shibuya for shopping, Shinjuku for nightlife, Asakusa for traditional temples, and Akihabara for electronics and anime culture."
        if "food" in last_lower and "tokyo" in last_lower:
            return "Must-try dishes in Tokyo include fresh sushi at Tsukiji, ramen in Shinjuku, tempura, yakitori, and matcha desserts in Asakusa."
        if "kyoto" in last_lower and "temple" in last_lower:
            return "In Kyoto, visit Kinkaku-ji (Golden Pavilion), Fushimi Inari with its thousand torii gates, and Arashiyama bamboo grove."
        if "itinerary" in last_lower or "summarize" in last_lower:
            return "Here's your Japan itinerary: 3 days in Tokyo (Shibuya, Shinjuku, Asakusa), then Kyoto for temples (Kinkaku-ji, Fushimi Inari). We also discussed Osaka for food."
        if "first city" in last_lower:
            return "The first city you mentioned wanting to visit was Japan, specifically starting with Tokyo."
        if "how many days" in last_lower:
            return "You said you'd spend 3 days in Tokyo exploring neighborhoods like Shibuya and Shinjuku."

        # Code-related context-aware responses
        if "bubble sort" in last_lower and "review" in last_lower:
            return "Bubble sort works by repeatedly swapping adjacent elements. It's simple but inefficient for large datasets due to O(n^2) complexity."
        if "time complexity" in last_lower:
            return "Bubble sort has O(n^2) time complexity in worst and average cases, and O(n) best case when already sorted."
        if "efficient" in last_lower and "sort" in last_lower:
            return "Merge sort is more efficient with O(n log n) time complexity. Quick sort is also good on average but O(n^2) worst case."
        if "merge sort" in last_lower and ("write" in last_lower or "implement" in last_lower):
            return "Here's merge sort in Python:\ndef merge_sort(arr):\n    if len(arr) <= 1: return arr\n    mid = len(arr)//2\n    return merge(merge_sort(arr[:mid]), merge_sort(arr[mid:]))"
        if "compare" in last_lower and ("bubble" in last_lower or "merge" in last_lower):
            return "Bubble sort is O(n^2) and simple but slow. Merge sort is O(n log n), faster for large data but uses more memory. Both are stable sorts."
        if "first algorithm" in last_lower:
            return "The first algorithm you asked about was bubble sort, which we reviewed for its time complexity."
        if "language" in last_lower and "merge sort" in last_lower:
            return "You asked me to write the merge sort implementation in Python."

        # Efficiency probe responses
        if "capital" in last_lower and "france" in last_lower:
            base = "The capital of France is Paris."
            return base + " It has been the capital since the 10th century and is known for the Eiffel Tower." if verbose else base
        if "hash table" in last_lower:
            base = "A hash table is a data structure that maps keys to values using a hash function."
            if verbose:
                return base + " The hash function converts keys into array indices for O(1) average lookup time. Collisions are handled via chaining or open addressing."
            return base + " It provides O(1) average-case lookup, insertion, and deletion."
        if "exercise" in last_lower or "benefits" in last_lower:
            base = "1. Improves cardiovascular health\n2. Boosts mental well-being\n3. Strengthens muscles and bones"
            if verbose:
                return base + "\n\nExercise releases endorphins which improve mood. Regular physical activity reduces risk of chronic diseases like diabetes and heart disease."
            return base

        # Generic fallback with turn-based variation
        fallbacks = [
            "That's a great question. Based on what we've discussed, I think the key point is about finding the right balance.",
            "Looking at this from a practical perspective, there are several factors to consider in this situation.",
            "I'd approach this by first understanding the core requirements and then building from there.",
            "This connects to what we talked about earlier. The main insight is about understanding the fundamentals.",
            "From my analysis, the most important aspect here is to focus on clarity and simplicity.",
        ]
        return fallbacks[self._mock_turn % len(fallbacks)]

    def _mock_json_response(self, prompt: str) -> LLMResponse:
        # Simulate occasional failures
        r = random.random()
        if r < 0.15:
            content = '{"name": "Alice", "age": 30, "email": "alice@example.com"'  # broken
        elif r < 0.25:
            content = '{"name": "Alice", "age": "thirty", "email": "alice@example.com"}'  # wrong type
        else:
            content = json.dumps({
                "name": "Alice",
                "age": 30,
                "email": "alice@example.com",
                "city": "Seoul",
            })
        tokens = len(content.split())
        return LLMResponse(content=content, prompt_tokens=20, completion_tokens=tokens, total_tokens=20 + tokens, model="mock-model")

    def _mock_yaml_response(self, prompt: str) -> LLMResponse:
        r = random.random()
        if r < 0.15:
            content = "name: Alice\n  age: 30\n city: Seoul"  # bad indentation
        else:
            content = "name: Alice\nage: 30\nemail: alice@example.com\ncity: Seoul"
        tokens = len(content.split())
        return LLMResponse(content=content, prompt_tokens=15, completion_tokens=tokens, total_tokens=15 + tokens, model="mock-model")
