"""Ollama model client with mock fallback.

Provides a unified interface for interacting with LLM models.
When Ollama is available, uses the real REST API.
When unavailable, falls back to a deterministic mock that simulates
model behavior for demonstration purposes.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass

import httpx


OLLAMA_BASE_URL = "http://localhost:11434"

# Default model names (configurable)
SMALL_MODEL = "qwen2.5:0.5b"
LARGE_MODEL = "qwen2.5:7b"


@dataclass
class ModelResponse:
    model: str
    text: str
    eval_count: int  # tokens generated
    eval_duration_ms: float
    is_mock: bool = False


def check_ollama_available() -> bool:
    """Check if Ollama server is running and reachable."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def list_available_models() -> list[str]:
    """List models available in Ollama."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def generate(model: str, prompt: str, system: str = "") -> ModelResponse:
    """Generate a response from the given model.

    Tries Ollama first, falls back to mock if unavailable.
    """
    if check_ollama_available():
        return _generate_ollama(model, prompt, system)
    return _generate_mock(model, prompt, system)


def _generate_ollama(model: str, prompt: str, system: str) -> ModelResponse:
    """Call the real Ollama /api/generate endpoint."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system

    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()

    return ModelResponse(
        model=model,
        text=data.get("response", ""),
        eval_count=data.get("eval_count", 0),
        eval_duration_ms=data.get("eval_duration", 0) / 1e6,
    )


# --- Mock responses for demonstration ---

_MOCK_RESPONSES: dict[str, dict[str, str]] = {
    "small": {
        "summary": (
            "The article discusses recent advances in renewable energy, "
            "highlighting solar panel efficiency improvements and cost reductions. "
            "Key points include a 30% efficiency gain in perovskite cells "
            "and declining manufacturing costs across the industry."
        ),
        "translation": (
            "인공지능(AI)은 컴퓨터 과학의 한 분야로, "
            "인간의 학습, 추론, 자기 수정 등의 지능적 행동을 "
            "컴퓨터가 모방할 수 있도록 하는 기술입니다."
        ),
        "simple_qa": (
            "Python is a high-level, interpreted programming language known "
            "for its readable syntax and versatility. It was created by "
            "Guido van Rossum and first released in 1991."
        ),
        "code_simple": (
            "```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n"
            "    a, b = 0, 1\n    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n    return b\n```"
        ),
        "code_complex": (
            "Here's a basic attempt at a binary search tree:\n"
            "```python\nclass Node:\n    def __init__(self, val):\n"
            "        self.val = val\n        self.left = None\n"
            "        self.right = None\n\ndef insert(root, val):\n"
            "    if not root:\n        return Node(val)\n"
            "    # ... (incomplete implementation)\n```\n"
            "I'm not fully confident about the balancing and edge cases."
        ),
        "design": (
            "I think you could maybe use a counter... "
            "but I'm not sure how to handle distributed state. "
            "Perhaps Redis? I'm not confident about the approach."
        ),
        "analysis": (
            "The main factors seem to be supply and demand, but I'm not "
            "sure about all the nuances of market microstructure. "
            "This might need a more detailed analysis."
        ),
        "reasoning": (
            "I think it might be related to a few factors... "
            "but I'm not sure. Perhaps it's not certain. "
            "I need more information to give a complete answer."
        ),
    },
    "large": {
        "summary": (
            "The article presents a comprehensive analysis of renewable energy advances:\n"
            "1. **Solar**: Perovskite cell efficiency reached 33.7%, a 30% improvement.\n"
            "2. **Cost**: Manufacturing costs dropped 45% over 3 years.\n"
            "3. **Policy**: 47 countries adopted new green energy mandates.\n"
            "4. **Impact**: Projected to offset 2.3GT CO2 annually by 2030."
        ),
        "code_complex": (
            "Here's a complete, self-balancing AVL tree implementation:\n"
            "```python\nclass AVLNode:\n    def __init__(self, key):\n"
            "        self.key = key\n        self.left = None\n"
            "        self.right = None\n        self.height = 1\n\n"
            "class AVLTree:\n    def _height(self, node):\n"
            "        return node.height if node else 0\n\n"
            "    def _balance_factor(self, node):\n"
            "        return self._height(node.left) - self._height(node.right)\n\n"
            "    def _rotate_right(self, y):\n"
            "        x = y.left\n        T2 = x.right\n"
            "        x.right = y\n        y.left = T2\n"
            "        y.height = 1 + max(self._height(y.left), self._height(y.right))\n"
            "        x.height = 1 + max(self._height(x.left), self._height(x.right))\n"
            "        return x\n\n"
            "    def _rotate_left(self, x):\n"
            "        y = x.right\n        T2 = y.left\n"
            "        y.left = x\n        x.right = T2\n"
            "        x.height = 1 + max(self._height(x.left), self._height(x.right))\n"
            "        y.height = 1 + max(self._height(y.left), self._height(y.right))\n"
            "        return y\n\n"
            "    def insert(self, root, key):\n"
            "        if not root:\n            return AVLNode(key)\n"
            "        if key < root.key:\n"
            "            root.left = self.insert(root.left, key)\n"
            "        else:\n"
            "            root.right = self.insert(root.right, key)\n"
            "        root.height = 1 + max(self._height(root.left), self._height(root.right))\n"
            "        balance = self._balance_factor(root)\n"
            "        # Left-Left\n        if balance > 1 and key < root.left.key:\n"
            "            return self._rotate_right(root)\n"
            "        # Right-Right\n        if balance < -1 and key > root.right.key:\n"
            "            return self._rotate_left(root)\n"
            "        # Left-Right\n        if balance > 1 and key > root.left.key:\n"
            "            root.left = self._rotate_left(root.left)\n"
            "            return self._rotate_right(root)\n"
            "        # Right-Left\n        if balance < -1 and key < root.right.key:\n"
            "            root.right = self._rotate_right(root.right)\n"
            "            return self._rotate_left(root)\n"
            "        return root\n```"
        ),
        "design": (
            "Here's a distributed rate limiter design using sliding windows:\n\n"
            "**Architecture**:\n"
            "- Each server maintains a local counter in a shared Redis cluster\n"
            "- Sliding window = fixed window + weighted previous window\n\n"
            "**Algorithm**:\n"
            "1. Divide time into fixed windows (e.g., 1-minute buckets)\n"
            "2. For current request at time t within window:\n"
            "   - weight = (window_size - elapsed) / window_size\n"
            "   - rate = prev_count * weight + current_count\n"
            "3. If rate > limit, reject; otherwise increment and allow\n\n"
            "**Trade-offs**:\n"
            "- **Consistency vs Performance**: Strict consistency requires "
            "synchronous Redis calls (higher latency); eventual consistency "
            "allows local counters with periodic sync (lower latency, slight over-admission)\n"
            "- **Memory vs Precision**: More granular windows = more memory but better accuracy"
        ),
        "analysis": (
            "Market dynamics are driven by multiple interconnected factors:\n\n"
            "1. **Supply/Demand**: Core price discovery mechanism where "
            "marginal buyers meet marginal sellers.\n"
            "2. **Market Microstructure**: Order book depth, bid-ask spreads, "
            "and latency affect short-term price movements.\n"
            "3. **Information Asymmetry**: Insiders and informed traders "
            "create adverse selection costs for market makers.\n"
            "4. **Behavioral Factors**: Herd behavior, anchoring bias, "
            "and loss aversion systematically distort rational pricing.\n"
            "5. **Regulatory Framework**: Position limits, circuit breakers, "
            "and reporting requirements shape market structure."
        ),
        "reasoning": (
            "Let me analyze this systematically:\n\n"
            "**Step 1 — Identify Variables**: We have three interacting systems "
            "with feedback loops.\n"
            "**Step 2 — Causal Chain**: A → B (direct positive), B → C (inverse), "
            "C → A (delayed positive feedback).\n"
            "**Step 3 — Equilibrium Analysis**: The system converges to a "
            "stable equilibrium when dA/dt = dB/dt = dC/dt = 0.\n"
            "**Step 4 — Sensitivity**: Variable B is the bottleneck; "
            "a 10% change in B cascades to 23% change in system output.\n"
            "**Conclusion**: Focus optimization on variable B for maximum impact."
        ),
    },
}


def _classify_mock_task(prompt: str) -> str:
    """Classify the prompt into a mock task category."""
    prompt_lower = prompt.lower()
    # Check most specific patterns first
    if any(w in prompt_lower for w in ["summarize", "summary", "요약", "tl;dr"]):
        return "summary"
    if any(w in prompt_lower for w in ["translate", "번역"]):
        return "translation"
    if any(w in prompt_lower for w in ["what is", "what are", "define", "뭐야",
                                        "무엇"]):
        return "simple_qa"
    if any(w in prompt_lower for w in ["function", "fibonacci", "hello world",
                                        "simple code", "간단한 코드"]):
        return "code_simple"
    if any(w in prompt_lower for w in ["implement", "write code", "코드",
                                        "data structure", "avl", "tree", "sort"]):
        return "code_complex"
    if any(w in prompt_lower for w in ["design", "architect", "algorithm"]):
        return "design"
    if any(w in prompt_lower for w in ["analyze", "분석", "market", "시장",
                                        "economics", "경제"]):
        return "analysis"
    if any(w in prompt_lower for w in ["reason", "추론", "logic", "논리",
                                        "explain why", "step by step", "why"]):
        return "reasoning"
    return "simple_qa"


def _generate_mock(model: str, prompt: str, system: str) -> ModelResponse:
    """Generate a mock response simulating model behavior."""
    is_small = model == SMALL_MODEL or "small" in model.lower() or "0.5b" in model
    size_key = "small" if is_small else "large"
    task = _classify_mock_task(prompt)

    responses = _MOCK_RESPONSES[size_key]
    text = responses.get(task, responses.get("simple_qa", "I can help with that."))

    # Simulate timing — small model is faster
    base_time = 200 if is_small else 800
    jitter = random.uniform(0.8, 1.2)
    simulated_ms = base_time * jitter

    token_count = len(text.split()) * 1.3  # rough token estimate

    time.sleep(0.1)  # brief delay to feel realistic

    return ModelResponse(
        model=model,
        text=text,
        eval_count=int(token_count),
        eval_duration_ms=simulated_ms,
        is_mock=True,
    )
