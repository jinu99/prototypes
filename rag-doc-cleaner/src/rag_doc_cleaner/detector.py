"""Noise detection: watermarks, repeated headers/footers, OCR artifacts."""

import re
from collections import Counter
from dataclasses import dataclass, field

from .extractor import DocumentData, TextBlock

# OCR artifact patterns
RE_GARBLED = re.compile(r"[~!@#$%^&*()|{}\[\]\\/<>]{3,}")
RE_BROKEN_UTF8 = re.compile(r"Ã[\x80-\xbf]")
RE_SCAN_LINE = re.compile(r"^[\s._\-=|/\\:■□?]+$")
RE_REPEATED_QMARK = re.compile(r"\?{3,}")


@dataclass
class WatermarkHit:
    text: str
    pages: list[int]
    avg_font_size: float
    is_light_color: bool


@dataclass
class HeaderFooterHit:
    text: str
    zone: str  # "header" or "footer"
    pages: list[int]
    pattern: str  # text with page numbers replaced by {n}


@dataclass
class OCRArtifactHit:
    text: str
    page_num: int
    reason: str  # e.g. "garbled_chars", "broken_encoding", "scan_line"


@dataclass
class DiagnosisReport:
    watermarks: list[WatermarkHit] = field(default_factory=list)
    headers_footers: list[HeaderFooterHit] = field(default_factory=list)
    ocr_artifacts: list[OCRArtifactHit] = field(default_factory=list)
    total_pages: int = 0
    total_blocks: int = 0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_pages": self.total_pages,
                "total_blocks": self.total_blocks,
                "watermarks_found": len(self.watermarks),
                "headers_footers_found": len(self.headers_footers),
                "ocr_artifacts_found": len(self.ocr_artifacts),
            },
            "watermarks": [
                {
                    "text": w.text,
                    "pages": [p + 1 for p in w.pages],
                    "avg_font_size": round(w.avg_font_size, 1),
                    "is_light_color": w.is_light_color,
                }
                for w in self.watermarks
            ],
            "headers_footers": [
                {
                    "text_sample": h.text,
                    "zone": h.zone,
                    "pages": [p + 1 for p in h.pages],
                    "pattern": h.pattern,
                }
                for h in self.headers_footers
            ],
            "ocr_artifacts": [
                {
                    "text": a.text,
                    "page": a.page_num + 1,
                    "reason": a.reason,
                }
                for a in self.ocr_artifacts
            ],
        }


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for cross-page comparison (strip page numbers).

    Only replaces standalone numbers that look like page numbers — not numbers
    embedded in model names, codes, or other structured identifiers.
    """
    # Match digits only when surrounded by spaces, punctuation, or string boundaries
    # but NOT when preceded/followed by letters or hyphens (e.g., X-200, Rev.3)
    normalized = re.sub(r"(?<![a-zA-Z0-9\-.])\d{1,3}(?![a-zA-Z0-9\-.])", "{n}", text.strip())
    return normalized


def _is_light_color(color: tuple) -> bool:
    """Check if a color is light (gray or near-white)."""
    r, g, b = color
    return r > 150 and g > 150 and b > 150


def detect_watermarks(doc: DocumentData) -> list[WatermarkHit]:
    """Detect watermark text: large, light-colored, centered, repeated across pages."""
    hits: list[WatermarkHit] = []

    # Group centered blocks with large font sizes
    candidates: dict[str, list[TextBlock]] = {}
    for page in doc.pages:
        for block in page.blocks:
            if block.font_size >= 36 and block.is_center_zone:
                key = block.text.strip()
                if key not in candidates:
                    candidates[key] = []
                candidates[key].append(block)

    min_pages = max(2, doc.total_pages * 0.5)
    for text, blocks in candidates.items():
        pages = sorted(set(b.page_num for b in blocks))
        if len(pages) >= min_pages:
            avg_fs = sum(b.font_size for b in blocks) / len(blocks)
            light = any(_is_light_color(b.color) for b in blocks)
            hits.append(WatermarkHit(
                text=text,
                pages=pages,
                avg_font_size=avg_fs,
                is_light_color=light,
            ))

    return hits


def detect_headers_footers(doc: DocumentData) -> list[HeaderFooterHit]:
    """Detect repeated headers and footers across pages."""
    hits: list[HeaderFooterHit] = []
    if doc.total_pages < 2:
        return hits

    # Collect top-zone and bottom-zone blocks
    for zone_name, zone_check in [("header", "is_top_zone"), ("footer", "is_bottom_zone")]:
        patterns: dict[str, list[tuple[str, int]]] = {}
        for page in doc.pages:
            for block in page.blocks:
                if getattr(block, zone_check):
                    normalized = _normalize_for_comparison(block.text)
                    if normalized not in patterns:
                        patterns[normalized] = []
                    patterns[normalized].append((block.text, page.page_num))

        min_pages = max(2, doc.total_pages * 0.5)
        for pattern, occurrences in patterns.items():
            pages = sorted(set(pn for _, pn in occurrences))
            if len(pages) >= min_pages:
                sample_text = occurrences[0][0]
                hits.append(HeaderFooterHit(
                    text=sample_text,
                    zone=zone_name,
                    pages=pages,
                    pattern=pattern,
                ))

    return hits


def detect_ocr_artifacts(doc: DocumentData) -> list[OCRArtifactHit]:
    """Detect OCR artifacts: garbled chars, broken encodings, scan lines."""
    hits: list[OCRArtifactHit] = []

    for page in doc.pages:
        for block in page.blocks:
            for line in block.text.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # Check for garbled character sequences
                if RE_GARBLED.search(line_stripped):
                    hits.append(OCRArtifactHit(
                        text=line_stripped,
                        page_num=page.page_num,
                        reason="garbled_chars",
                    ))
                    continue

                # Check for broken UTF-8 encoding artifacts
                if RE_BROKEN_UTF8.search(line_stripped):
                    hits.append(OCRArtifactHit(
                        text=line_stripped,
                        page_num=page.page_num,
                        reason="broken_encoding",
                    ))
                    continue

                # Check for repeated question marks (font rendering failures)
                if RE_REPEATED_QMARK.match(line_stripped):
                    hits.append(OCRArtifactHit(
                        text=line_stripped,
                        page_num=page.page_num,
                        reason="garbled_chars",
                    ))
                    continue

                # Check for scan line artifacts (lines of only special chars)
                if RE_SCAN_LINE.match(line_stripped) and len(line_stripped) >= 3:
                    hits.append(OCRArtifactHit(
                        text=line_stripped,
                        page_num=page.page_num,
                        reason="scan_line",
                    ))

    return hits


def diagnose(doc: DocumentData) -> DiagnosisReport:
    """Run all detection algorithms and produce a report."""
    total_blocks = sum(len(p.blocks) for p in doc.pages)

    report = DiagnosisReport(
        watermarks=detect_watermarks(doc),
        headers_footers=detect_headers_footers(doc),
        ocr_artifacts=detect_ocr_artifacts(doc),
        total_pages=doc.total_pages,
        total_blocks=total_blocks,
    )
    return report
