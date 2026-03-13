"""Context snippet generator for LLM prompts with token budget."""

from .checker import cosine_similarity, embed_fact, get_model
from .db import Fact


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def generate_context_snippet(
    scene_text: str,
    all_facts: list[Fact],
    token_budget: int = 2000,
) -> str:
    """Select facts relevant to a scene within a token budget.

    Uses embedding similarity to rank facts by relevance to the scene,
    then packs the most relevant ones within the budget.
    """
    if not all_facts:
        return "No facts available in database."

    model = get_model()
    scene_embedding = model.encode(
        scene_text[:1000], normalize_embeddings=True
    ).tolist()

    # Score each fact by similarity to the scene
    scored: list[tuple[float, Fact]] = []
    for fact in all_facts:
        emb = fact.embedding or embed_fact(fact)
        sim = cosine_similarity(scene_embedding, emb)
        scored.append((sim, fact))

    scored.sort(key=lambda x: -x[0])

    # Build snippet within budget
    header = "## Relevant Facts for Current Scene\n\n"
    budget_remaining = token_budget - estimate_tokens(header)
    lines: list[str] = []
    entities_seen: dict[str, list[str]] = {}

    for sim, fact in scored:
        if sim < 0.1:
            break
        line = f"- **{fact.entity}**.{fact.attribute} = {fact.value}"
        line += f"  _(from {fact.chapter}, line {fact.line_start})_"
        cost = estimate_tokens(line)
        if cost > budget_remaining:
            break
        budget_remaining -= cost
        lines.append(line)

        # Track entities
        if fact.entity not in entities_seen:
            entities_seen[fact.entity] = []
        entities_seen[fact.entity].append(fact.attribute)

    if not lines:
        return "No relevant facts found for this scene."

    result = header
    result += f"_Token budget: {token_budget}, used: ~{token_budget - budget_remaining}_\n\n"
    result += "\n".join(lines)
    result += f"\n\n_({len(lines)} facts selected, {len(entities_seen)} entities)_"
    return result
