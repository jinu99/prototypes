"""Complexity-based smart router.

Uses TF-IDF features + keyword heuristics to classify request complexity
and route to the appropriate model (small or large).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from agent_mesh.models import SMALL_MODEL, LARGE_MODEL


class Complexity(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


@dataclass
class RoutingDecision:
    complexity: Complexity
    model: str
    score: float  # 0.0 = definitely simple, 1.0 = definitely complex
    reasons: list[str]


# Training data for the complexity classifier
_TRAIN_PROMPTS = [
    # Simple tasks
    ("Summarize this article in 3 sentences", Complexity.SIMPLE),
    ("What is Python?", Complexity.SIMPLE),
    ("Translate this to Korean", Complexity.SIMPLE),
    ("Write a hello world program", Complexity.SIMPLE),
    ("What is the capital of France?", Complexity.SIMPLE),
    ("이 문장을 요약해줘", Complexity.SIMPLE),
    ("Define machine learning", Complexity.SIMPLE),
    ("List 5 fruits", Complexity.SIMPLE),
    ("Write a fibonacci function", Complexity.SIMPLE),
    ("Convert Celsius to Fahrenheit", Complexity.SIMPLE),
    ("Explain what a variable is", Complexity.SIMPLE),
    ("What does HTML stand for?", Complexity.SIMPLE),
    # Complex tasks
    ("Implement a self-balancing AVL tree with delete operations", Complexity.COMPLEX),
    ("Design a microservice architecture for an e-commerce platform", Complexity.COMPLEX),
    ("Analyze the economic implications of quantitative easing", Complexity.COMPLEX),
    ("Write a compiler for a simple expression language", Complexity.COMPLEX),
    ("Implement a distributed consensus algorithm", Complexity.COMPLEX),
    ("Explain the proof of Gödel's incompleteness theorem", Complexity.COMPLEX),
    ("Design a database schema with normalization for a hospital", Complexity.COMPLEX),
    ("Compare and contrast 5 sorting algorithms with trade-offs", Complexity.COMPLEX),
    ("Write a neural network from scratch", Complexity.COMPLEX),
    ("Implement a garbage collector", Complexity.COMPLEX),
    ("Design a rate limiter with sliding window algorithm", Complexity.COMPLEX),
    ("Analyze multi-variable calculus optimization problem", Complexity.COMPLEX),
]

# Keywords that strongly indicate complexity
_COMPLEX_KEYWORDS = [
    "implement", "design", "architect", "optimize", "analyze",
    "compare and contrast", "trade-off", "algorithm", "data structure",
    "distributed", "concurrent", "proof", "theorem", "from scratch",
    "neural network", "compiler", "microservice", "normalization",
    "설계", "구현", "최적화", "분석", "아키텍처",
]

_SIMPLE_KEYWORDS = [
    "what is", "define", "list", "summarize", "translate",
    "hello world", "explain", "convert", "simple",
    "뭐야", "무엇", "요약", "번역", "간단",
]


class ComplexityRouter:
    """Routes requests to small or large models based on complexity."""

    def __init__(
        self,
        small_model: str = SMALL_MODEL,
        large_model: str = LARGE_MODEL,
        complexity_threshold: float = 0.5,
    ):
        self.small_model = small_model
        self.large_model = large_model
        self.threshold = complexity_threshold
        self._vectorizer = TfidfVectorizer(
            max_features=200,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self._classifier = LogisticRegression(max_iter=1000)
        self._train()

    def _train(self) -> None:
        """Train the TF-IDF + Logistic Regression classifier."""
        texts = [p for p, _ in _TRAIN_PROMPTS]
        labels = [1 if c == Complexity.COMPLEX else 0 for _, c in _TRAIN_PROMPTS]
        X = self._vectorizer.fit_transform(texts)
        self._classifier.fit(X, labels)

    def route(self, prompt: str) -> RoutingDecision:
        """Classify prompt complexity and decide which model to use."""
        reasons = []

        # TF-IDF classifier score
        X = self._vectorizer.transform([prompt])
        proba = self._classifier.predict_proba(X)[0]
        ml_score = proba[1]  # probability of "complex"
        reasons.append(f"ML classifier confidence: {ml_score:.2f}")

        # Keyword heuristic boost
        prompt_lower = prompt.lower()
        keyword_score = 0.0
        complex_hits = [kw for kw in _COMPLEX_KEYWORDS if kw in prompt_lower]
        simple_hits = [kw for kw in _SIMPLE_KEYWORDS if kw in prompt_lower]

        if complex_hits:
            keyword_score += 0.15 * len(complex_hits)
            reasons.append(f"Complex keywords: {complex_hits}")
        if simple_hits:
            keyword_score -= 0.15 * len(simple_hits)
            reasons.append(f"Simple keywords: {simple_hits}")

        # Length heuristic — longer prompts tend to be more complex
        word_count = len(prompt.split())
        if word_count > 30:
            keyword_score += 0.1
            reasons.append(f"Long prompt ({word_count} words)")
        elif word_count < 10:
            keyword_score -= 0.05
            reasons.append(f"Short prompt ({word_count} words)")

        # Combined score (clamp to 0-1)
        final_score = max(0.0, min(1.0, ml_score + keyword_score))
        complexity = Complexity.COMPLEX if final_score >= self.threshold else Complexity.SIMPLE
        model = self.large_model if complexity == Complexity.COMPLEX else self.small_model

        reasons.append(f"Final score: {final_score:.2f} (threshold: {self.threshold})")
        reasons.append(f"Decision: {complexity.value} → {model}")

        return RoutingDecision(
            complexity=complexity,
            model=model,
            score=final_score,
            reasons=reasons,
        )
