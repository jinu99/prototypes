"""PDF text extraction with positional metadata using PyMuPDF."""

from dataclasses import dataclass, field

import fitz


@dataclass
class TextBlock:
    """A text block extracted from a PDF page."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    font_size: float = 0.0
    color: tuple = (0, 0, 0)

    @property
    def is_top_zone(self) -> bool:
        """Block is in the top 8% of the page (header zone)."""
        return self.y0 < 842 * 0.08

    @property
    def is_bottom_zone(self) -> bool:
        """Block is in the bottom 5% of the page (footer zone)."""
        return self.y1 > 842 * 0.95

    @property
    def is_center_zone(self) -> bool:
        """Block is roughly centered on the page."""
        page_cx = 595 / 2
        block_cx = (self.x0 + self.x1) / 2
        return abs(block_cx - page_cx) < 100


@dataclass
class PageData:
    """Extracted data for a single PDF page."""

    page_num: int
    width: float
    height: float
    blocks: list[TextBlock] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


@dataclass
class DocumentData:
    """Extracted data for an entire PDF document."""

    path: str
    pages: list[PageData] = field(default_factory=list)

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.full_text for p in self.pages)


def extract_document(pdf_path: str) -> DocumentData:
    """Extract text blocks with positional metadata from a PDF."""
    doc = fitz.open(pdf_path)
    document = DocumentData(path=pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_data = PageData(
            page_num=page_num,
            width=page.rect.width,
            height=page.rect.height,
        )

        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] != 0:  # text blocks only
                continue

            text_parts = []
            max_fontsize = 0.0
            color = (0, 0, 0)

            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    line_text += span["text"]
                    if span["size"] > max_fontsize:
                        max_fontsize = span["size"]
                        # fitz returns color as int, convert to RGB tuple
                        c = span.get("color", 0)
                        color = (
                            (c >> 16) & 0xFF,
                            (c >> 8) & 0xFF,
                            c & 0xFF,
                        )
                text_parts.append(line_text)

            text = "\n".join(text_parts).strip()
            if not text:
                continue

            bbox = block["bbox"]
            tb = TextBlock(
                text=text,
                x0=bbox[0],
                y0=bbox[1],
                x1=bbox[2],
                y1=bbox[3],
                page_num=page_num,
                font_size=max_fontsize,
                color=color,
            )
            page_data.blocks.append(tb)

        document.pages.append(page_data)

    doc.close()
    return document
