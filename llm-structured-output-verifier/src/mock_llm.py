"""Mock LLM that simulates extraction and verification.

Deliberately introduces some hallucinated fields to demonstrate
the 2-pass verification catching them.
"""

import re
from typing import Any


def _find_exact_span(text: str, query: str) -> str | None:
    """Find exact substring match in text."""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return None
    start = max(0, idx - 10)
    end = min(len(text), idx + len(query) + 10)
    return text[start:end].strip()


def _find_partial_span(text: str, query: str) -> tuple[str | None, float]:
    """Find partial match. Returns (span, word_match_ratio)."""
    text_lower = text.lower()
    words = [w for w in query.lower().split() if len(w) > 3]
    if not words:
        return None, 0.0

    matched = sum(1 for w in words if w in text_lower)
    ratio = matched / len(words)

    # Find first matching word for span
    span = None
    for w in words:
        idx = text_lower.find(w)
        if idx != -1:
            start = max(0, idx - 20)
            end = min(len(text), idx + len(w) + 20)
            span = text[start:end].strip()
            break

    return span, ratio


def _extract_person(text: str) -> dict:
    """Extract person profile with some deliberate hallucinations."""
    result: dict[str, Any] = {}
    text_lower = text.lower()

    # Name extraction via heuristics
    name_patterns = [
        r"(?:name(?:d)?|called|is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:is|was|has|works)",
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            result["name"] = m.group(1).strip()
            break
    if "name" not in result:
        result["name"] = "Unknown"

    # Age
    age_m = re.search(r"(\d{1,2})[\s-]*(?:year|yr)s?[\s-]*old", text_lower)
    if age_m:
        result["age"] = int(age_m.group(1))
    else:
        # HALLUCINATION: invent an age when not found
        result["age"] = 34

    # Occupation
    occ_patterns = [
        r"(?:works?\s+as\s+(?:a\s+)?)([^,.]+?)(?:\s+(?:at|for|in|who)\b|,|\.|$)",
        r"is\s+(?:a\s+)?([\w\s]+?(?:engineer|scientist|analyst|developer|manager|designer|director|professor|researcher|consultant))",
    ]
    for pat in occ_patterns:
        m = re.search(pat, text_lower)
        if m:
            result["occupation"] = m.group(1).strip().title()
            break
    if "occupation" not in result:
        result["occupation"] = None

    # Company
    comp_m = re.search(r"(?:at|for|with|joined|works at)\s+([A-Z][A-Za-z\s&]+?)(?:\s+(?:as|in|where|since|,|\.))", text)
    if comp_m:
        result["company"] = comp_m.group(1).strip()
    else:
        # HALLUCINATION: invent company
        result["company"] = "TechVentures Inc."

    # Education
    edu_m = re.search(
        r"(?:graduated?\s+from|studied\s+at|degree\s+from|alumni?\s+of|attended)\s+([^,.]+)",
        text_lower,
    )
    if edu_m:
        result["education"] = edu_m.group(1).strip().title()
    else:
        result["education"] = None

    # Location
    loc_m = re.search(r"(?:based\s+in|lives?\s+in|located\s+in|from)\s+([A-Z][A-Za-z\s,]+?)(?:\.|,|$)", text)
    if loc_m:
        result["location"] = loc_m.group(1).strip()
    else:
        result["location"] = None

    # Achievements
    achievements = []
    ach_patterns = [
        r"(?:awarded?|won|received|earned)\s+([^,.]+)",
        r"(?:published|authored)\s+([^,.]+)",
    ]
    for pat in ach_patterns:
        for m in re.finditer(pat, text_lower):
            achievements.append(m.group(1).strip().title())
    # HALLUCINATION: add a fake achievement sometimes
    if "research" in text_lower or "science" in text_lower:
        achievements.append("Recipient of the National Science Innovation Award 2023")
    result["achievements"] = achievements

    return result


def _extract_product(text: str) -> dict:
    """Extract product info with some deliberate hallucinations."""
    result: dict[str, Any] = {}
    text_lower = text.lower()

    # Product name - try to find quoted or capitalized product names
    name_m = re.search(r'"([^"]+)"', text)
    if name_m:
        result["product_name"] = name_m.group(1)
    else:
        words = text.split()[:5]
        result["product_name"] = " ".join(w for w in words if w[0].isupper()) or "Unknown Product"

    # Brand
    brand_m = re.search(r"(?:by|from|made by|brand:?)\s+([A-Z][A-Za-z]+)", text)
    if brand_m:
        result["brand"] = brand_m.group(1)
    else:
        # HALLUCINATION: invent a brand
        result["brand"] = "ProTech Solutions"

    # Price
    price_m = re.search(r"\$[\d,.]+", text)
    if price_m:
        result["price"] = price_m.group(0)
    else:
        # HALLUCINATION: invent a price
        result["price"] = "$299.99"

    # Rating
    rating_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:/\s*\d+|out of \d+|stars?|⭐)", text_lower)
    if rating_m:
        result["rating"] = rating_m.group(0).strip()
    else:
        result["rating"] = None

    # Pros — look for positive sentiment sentences
    pros = []
    sentences = re.split(r"[.!]", text)
    for s in sentences:
        sl = s.strip().lower()
        if any(w in sl for w in ["incredible", "top-notch", "crisp", "excellent", "great", "love", "amazing", "smooth", "solid", "game-changer", "well worth", "whisper-quiet"]):
            pros.append(s.strip()[:80])
    result["pros"] = pros[:3]

    # Cons — look for negative sentiment sentences
    cons = []
    for s in sentences:
        sl = s.strip().lower()
        if any(w in sl for w in ["however", "complaint", "could be", "cheap", "confusing", "disappointing", "downside", "unfortunately"]):
            cons.append(s.strip()[:80])
    result["cons"] = cons[:3]

    return result


def _extract_event(text: str) -> dict:
    """Extract event info with some deliberate hallucinations."""
    result: dict[str, Any] = {}
    text_lower = text.lower()

    # Event name
    name_m = re.search(r'"([^"]+)"', text)
    if name_m:
        result["event_name"] = name_m.group(1)
    else:
        # Try first capitalized phrase
        cap_m = re.search(r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})", text)
        result["event_name"] = cap_m.group(1) if cap_m else "Unknown Event"

    # Date
    date_m = re.search(
        r"(?:on|date:?|scheduled\s+for|held\s+on)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
        text,
        re.IGNORECASE,
    )
    if date_m:
        result["date"] = date_m.group(1).strip()
    else:
        result["date"] = None

    # Location
    loc_m = re.search(r"(?:at|venue:?|held at|location:?)\s+([^,.]+)", text_lower)
    if loc_m:
        result["location"] = loc_m.group(1).strip().title()
    else:
        result["location"] = None

    # Organizer
    org_m = re.search(r"(?:organized?\s+by|hosted?\s+by|presented?\s+by|organizer:?)\s+([\w\s]+?)(?:\s+and\s+will|\s+in\s+|\.|,|$)", text_lower)
    if org_m:
        result["organizer"] = org_m.group(1).strip().title()
    else:
        # HALLUCINATION: invent organizer
        result["organizer"] = "Global Events Foundation"

    # Attendees
    att_m = re.search(r"(\d[\d,]*)\s*(?:attendees?|participants?|people|visitors?)", text_lower)
    if att_m:
        result["attendees"] = att_m.group(0).strip()
    else:
        # HALLUCINATION: invent attendee count
        result["attendees"] = "approximately 2,500 attendees"

    # Description
    result["description"] = text[:150].strip() + ("..." if len(text) > 150 else "")

    return result


EXTRACTORS = {
    "person": _extract_person,
    "product": _extract_product,
    "event": _extract_event,
}


def mock_extract(text: str, schema_type: str) -> dict:
    """Simulate 1-pass LLM extraction. May produce hallucinations."""
    extractor = EXTRACTORS.get(schema_type)
    if not extractor:
        raise ValueError(f"Unknown schema type: {schema_type}")
    return extractor(text)


def mock_verify_field(
    text: str, field_name: str, extracted_value: str
) -> dict:
    """Simulate 2nd-pass LLM verification of a single field.

    Returns evidence span, confidence, and reasoning.
    """
    if extracted_value is None or extracted_value == "" or extracted_value == "[]":
        return {
            "evidence_span": None,
            "confidence": 0.0,
            "reasoning": "No value to verify (field is empty/null)",
        }

    value_str = str(extracted_value)

    # Level 1: Exact substring match → high confidence
    exact_span = _find_exact_span(text, value_str)
    if exact_span:
        return {
            "evidence_span": exact_span,
            "confidence": 0.95,
            "reasoning": f"Exact textual evidence found for '{value_str}'",
        }

    # Level 2: Partial word overlap → medium confidence
    partial_span, ratio = _find_partial_span(text, value_str)
    if ratio >= 0.7:
        return {
            "evidence_span": partial_span,
            "confidence": 0.5 + 0.3 * ratio,
            "reasoning": f"Partial evidence: {ratio:.0%} of key words found in source",
        }
    if ratio >= 0.4:
        return {
            "evidence_span": partial_span,
            "confidence": 0.3 + 0.2 * ratio,
            "reasoning": f"Weak partial evidence: {ratio:.0%} of key words found in source",
        }

    # Level 3: No meaningful match → low confidence
    return {
        "evidence_span": None,
        "confidence": 0.1,
        "reasoning": f"No supporting evidence found in source text for '{value_str}'",
    }
