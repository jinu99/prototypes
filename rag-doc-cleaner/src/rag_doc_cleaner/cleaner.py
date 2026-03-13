"""Clean detected noise from document text and produce diff report."""

from dataclasses import dataclass, field

from .detector import DiagnosisReport, _normalize_for_comparison
from .extractor import DocumentData


@dataclass
class CleanedPage:
    page_num: int
    original_text: str
    cleaned_text: str
    removed_items: list[dict] = field(default_factory=list)


@dataclass
class CleanResult:
    pages: list[CleanedPage] = field(default_factory=list)
    total_removed: int = 0

    @property
    def cleaned_text(self) -> str:
        return "\n\n".join(
            p.cleaned_text for p in self.pages if p.cleaned_text.strip()
        )

    def diff_report(self) -> list[dict]:
        """Generate a per-page diff report of removed items."""
        report = []
        for page in self.pages:
            if page.removed_items:
                report.append({
                    "page": page.page_num + 1,
                    "removed": page.removed_items,
                    "original_length": len(page.original_text),
                    "cleaned_length": len(page.cleaned_text),
                    "reduction_pct": round(
                        (1 - len(page.cleaned_text) / max(len(page.original_text), 1)) * 100, 1
                    ),
                })
        return report


def clean_document(doc: DocumentData, report: DiagnosisReport) -> CleanResult:
    """Remove detected noise from document and return cleaned text."""
    # Build sets for fast lookup
    watermark_texts = {w.text.strip() for w in report.watermarks}
    hf_patterns = {h.pattern for h in report.headers_footers}
    artifact_texts = {a.text.strip() for a in report.ocr_artifacts}

    result = CleanResult()
    total_removed = 0

    for page in doc.pages:
        original_lines = []
        cleaned_lines = []
        removed = []

        for block in page.blocks:
            original_lines.append(block.text)
            block_text = block.text.strip()

            # Check watermark
            if block_text in watermark_texts:
                removed.append({"type": "watermark", "text": block_text})
                total_removed += 1
                continue

            # Check header/footer
            normalized = _normalize_for_comparison(block_text)
            if normalized in hf_patterns:
                removed.append({"type": "header_footer", "text": block_text})
                total_removed += 1
                continue

            # Filter OCR artifacts line by line within blocks
            cleaned_block_lines = []
            for line in block.text.split("\n"):
                line_stripped = line.strip()
                if line_stripped in artifact_texts:
                    removed.append({"type": "ocr_artifact", "text": line_stripped})
                    total_removed += 1
                elif line_stripped:
                    cleaned_block_lines.append(line)

            if cleaned_block_lines:
                cleaned_lines.append("\n".join(cleaned_block_lines))

        result.pages.append(CleanedPage(
            page_num=page.page_num,
            original_text="\n".join(original_lines),
            cleaned_text="\n".join(cleaned_lines),
            removed_items=removed,
        ))

    result.total_removed = total_removed
    return result
