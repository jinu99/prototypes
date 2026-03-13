"""Rule-based fact extraction from narrative text."""

import re
from pathlib import Path

from .db import Fact

# Chapter heading patterns
CHAPTER_RE = re.compile(
    r"^(?:chapter\s+(\d+|[ivxlc]+)(?:\s*[:\-–—]\s*(.*))?|#+\s*chapter\s+(\d+|[ivxlc]+)(?:\s*[:\-–—]\s*(.*))?)$",
    re.IGNORECASE | re.MULTILINE,
)

# --- Extraction patterns ---
# Each pattern: (regex, entity_group, attribute, value_group)

# "X had/has blue eyes" / "X had long dark hair"
PHYSICAL_HAD = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:had|has|have)\s+"
    r"([\w\s,\-]+?)\s+(eyes?|hair|skin|beard|scar|scars|height|build|voice)\b",
    re.IGNORECASE,
)

# "X was tall / X was a doctor"
WAS_DESCRIPTION = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:was|is|were)\s+"
    r"(a\s+)?(\w[\w\s,\-]{1,40}?)(?:\.|,|\band\b|;|$)",
    re.IGNORECASE,
)

# "X lived/lives in PLACE"
LOCATION = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:lived?|lives?|resides?|resided?|moved? to|grew up|born)\s+"
    r"(?:in|at|near|outside)\s+([A-Z][\w\s,]+?)(?:\.|,|;|\band\b|$)",
    re.IGNORECASE,
)

# "X's sister/brother/mother Y" or "Y, X's sister"
RELATIONSHIP = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)'s\s+"
    r"(mother|father|sister|brother|wife|husband|son|daughter|friend|mentor|partner|uncle|aunt|cousin|grandfather|grandmother)\s*,?\s+"
    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b",
    re.IGNORECASE,
)

# "X was N years old" / "X, aged N"
AGE = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*(?:,\s*aged\s+|was\s+|is\s+|turned\s+)(\d{1,3})\s*(?:years?\s*old)?\b",
    re.IGNORECASE,
)

# "X with ADJ eyes/hair"
WITH_PHYSICAL = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*,?\s*with\s+"
    r"(?:her|his|their)?\s*([\w\s,\-]+?)\s+(eyes?|hair|skin|beard|voice)\b",
    re.IGNORECASE,
)

# Attribute normalization
ATTR_MAP = {
    "eye": "eye_color", "eyes": "eye_color",
    "hair": "hair", "skin": "skin",
    "beard": "beard", "scar": "scar", "scars": "scar",
    "height": "height", "build": "build", "voice": "voice",
}

# Common non-character words to skip
SKIP_WORDS = {
    "the", "this", "that", "they", "there", "then", "than", "these",
    "those", "their", "them", "though", "through", "three", "thus",
    "he", "her", "his", "she", "its", "but", "and", "when", "while",
    "after", "before", "since", "until", "once", "every", "each",
    "chapter", "part", "book", "section", "page", "time",
    "old", "new", "young", "small", "large", "great", "big", "little",
    "first", "last", "next", "other", "same", "such", "many", "few",
}


def _is_valid_entity(name: str) -> bool:
    """Check if a name looks like a character name."""
    parts = name.split()
    for part in parts:
        if part.lower() in SKIP_WORDS:
            return False
        if not part[0].isupper():
            return False
    return len(name) >= 2


def _clean_value(val: str) -> str:
    return re.sub(r"\s+", " ", val).strip().rstrip(".,;")


def parse_chapters(text: str) -> list[tuple[str, int, int]]:
    """Split text into (chapter_name, start_line, end_line) tuples."""
    lines = text.split("\n")
    chapters = []
    current_chapter = "Prologue"
    current_start = 0

    for i, line in enumerate(lines):
        m = CHAPTER_RE.match(line.strip())
        if m:
            if i > current_start:
                chapters.append((current_chapter, current_start, i - 1))
            num = m.group(1) or m.group(3) or ""
            title = m.group(2) or m.group(4) or ""
            current_chapter = f"Chapter {num}"
            if title:
                current_chapter += f": {title.strip()}"
            current_start = i

    chapters.append((current_chapter, current_start, len(lines) - 1))
    return chapters


def extract_facts_from_text(
    text: str, source_file: str
) -> list[Fact]:
    """Extract structured facts from narrative text."""
    lines = text.split("\n")
    chapters = parse_chapters(text)
    facts: list[Fact] = []
    seen = set()  # deduplicate

    def _chapter_for_line(line_num: int) -> str:
        for name, start, end in chapters:
            if start <= line_num <= end:
                return name
        return "Unknown"

    def _add_fact(entity: str, attr: str, value: str, line_num: int, sentence: str):
        entity = entity.strip()
        if not _is_valid_entity(entity):
            return
        value = _clean_value(value)
        if not value or len(value) < 2:
            return
        key = (entity.lower(), attr.lower(), value.lower())
        if key in seen:
            return
        seen.add(key)
        chapter = _chapter_for_line(line_num)
        facts.append(Fact(
            entity=entity, attribute=attr, value=value,
            source_file=source_file, chapter=chapter,
            line_start=line_num + 1, line_end=line_num + 1,
            raw_sentence=sentence.strip()[:200],
        ))

    for i, line in enumerate(lines):
        # Physical: "X had blue eyes"
        for m in PHYSICAL_HAD.finditer(line):
            entity = m.group(1)
            desc = m.group(2)
            body_part = m.group(3).lower()
            attr = ATTR_MAP.get(body_part, body_part)
            _add_fact(entity, attr, _clean_value(desc), i, line)

        # "X with dark eyes"
        for m in WITH_PHYSICAL.finditer(line):
            entity = m.group(1)
            desc = m.group(2)
            body_part = m.group(3).lower()
            attr = ATTR_MAP.get(body_part, body_part)
            _add_fact(entity, attr, _clean_value(desc), i, line)

        # "X was a doctor" / "X was tall"
        for m in WAS_DESCRIPTION.finditer(line):
            entity = m.group(1)
            article = m.group(2) or ""
            desc = m.group(3)
            full_val = (article + desc).strip()
            # Determine attribute
            occupation_words = {
                "doctor", "teacher", "soldier", "knight", "merchant",
                "farmer", "priest", "scholar", "artist", "writer",
                "engineer", "blacksmith", "baker", "mage", "wizard",
            }
            age_words = {"young", "old", "elderly", "middle-aged"}
            height_words = {"tall", "short", "petite", "towering"}
            build_words = {"thin", "slender", "muscular", "heavy", "stocky", "lean"}

            first_word = desc.strip().split()[0].lower()
            if first_word in occupation_words or (article and article.strip() == "a"):
                attr = "occupation"
            elif first_word in age_words:
                attr = "age_description"
            elif first_word in height_words:
                attr = "height"
            elif first_word in build_words:
                attr = "build"
            else:
                attr = "description"
            _add_fact(entity, attr, full_val, i, line)

        # Location
        for m in LOCATION.finditer(line):
            entity = m.group(1)
            place = m.group(2)
            _add_fact(entity, "location", _clean_value(place), i, line)

        # Relationship
        for m in RELATIONSHIP.finditer(line):
            entity_a = m.group(1)
            rel = m.group(2).lower()
            entity_b = m.group(3)
            _add_fact(entity_a, f"has_{rel}", entity_b.strip(), i, line)
            # Inverse
            inverse = {
                "mother": "child_of", "father": "child_of",
                "sister": "sibling", "brother": "sibling",
                "wife": "spouse", "husband": "spouse",
                "son": "child_of", "daughter": "child_of",
                "friend": "friend", "mentor": "mentee_of",
                "partner": "partner",
            }
            if rel in inverse:
                _add_fact(entity_b, inverse[rel], entity_a.strip(), i, line)

        # Age
        for m in AGE.finditer(line):
            entity = m.group(1)
            age_val = m.group(2)
            _add_fact(entity, "age", age_val, i, line)

    return facts


def extract_from_file(filepath: str | Path) -> list[Fact]:
    """Read a text file and extract facts."""
    path = Path(filepath)
    text = path.read_text(encoding="utf-8")
    return extract_facts_from_text(text, path.name)
