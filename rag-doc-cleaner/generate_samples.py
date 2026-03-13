"""Generate sample PDFs with watermarks, headers/footers, and OCR artifacts."""

import fitz


def create_sample_report(path: str) -> None:
    """Corporate report with watermark + header/footer."""
    doc = fitz.open()
    header = "Acme Corp — Annual Report 2025"
    footer = "Confidential — Do Not Distribute — Page {n}"
    watermark = "DRAFT"
    body_texts = [
        (
            "Executive Summary\n\n"
            "This report outlines the strategic direction and financial performance "
            "of Acme Corp for the fiscal year 2025. Revenue grew by 23% year-over-year, "
            "driven primarily by the expansion into cloud services and the successful "
            "launch of our AI platform.\n\n"
            "Key highlights include a 15% reduction in operational costs through "
            "automation initiatives, and the acquisition of two strategic partners "
            "in the European market."
        ),
        (
            "Financial Overview\n\n"
            "Total revenue reached $4.2B, representing a compound annual growth rate "
            "of 18% over the past three years. The cloud services division contributed "
            "$1.8B, surpassing projections by 12%.\n\n"
            "Operating margins improved to 22%, up from 19% in the previous year. "
            "Free cash flow generation remained strong at $890M, enabling continued "
            "investment in R&D and strategic acquisitions."
        ),
        (
            "Strategic Outlook\n\n"
            "Looking ahead, Acme Corp will focus on three core pillars: expanding "
            "AI-driven product offerings, deepening partnerships in emerging markets, "
            "and accelerating the transition to sustainable operations.\n\n"
            "We project revenue growth of 20-25% for FY2026, with particular strength "
            "in the Asia-Pacific region where we plan to establish three new offices."
        ),
        (
            "Risk Factors\n\n"
            "Key risks include regulatory changes in data privacy across jurisdictions, "
            "potential supply chain disruptions, and increased competition in the "
            "cloud services market.\n\n"
            "Mitigation strategies are in place, including diversified supplier networks "
            "and proactive engagement with regulatory bodies."
        ),
    ]

    for i, body in enumerate(body_texts):
        page = doc.new_page(width=595, height=842)  # A4

        # Watermark — large, centered, rotated, light gray
        tw = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        fontsize = 72
        text_width = font.text_length(watermark, fontsize=fontsize)
        x = (page.rect.width - text_width) / 2
        y = page.rect.height / 2
        tw.append((x, y), watermark, font=font, fontsize=fontsize)
        tw.write_text(page, color=(0.85, 0.85, 0.85))

        # Header
        page.insert_text((50, 30), header, fontsize=9, color=(0.4, 0.4, 0.4))

        # Footer
        page.insert_text(
            (50, 820), footer.format(n=i + 1), fontsize=9, color=(0.4, 0.4, 0.4)
        )

        # Body text
        rect = fitz.Rect(50, 60, 545, 790)
        page.insert_textbox(rect, body, fontsize=11, color=(0, 0, 0))

    doc.save(path)
    doc.close()


def create_sample_ocr(path: str) -> None:
    """Document simulating OCR artifacts and broken encodings."""
    doc = fitz.open()
    header = "Scanned Document — Invoice #2847"
    footer = "Page {n} of 3"

    pages_content = [
        (
            "Invoice Details\n\n"
            "Bi11ed To: John Doe\n"  # OCR: 1 instead of l
            "Address: l23 Main St, Suite 4O1\n"  # OCR: l for 1, O for 0
            "Date: 2O25-O3-15\n\n"  # OCR: O for 0
            "Itern Description         Qty   Price\n"  # OCR: rn for m
            "Widget A1pha              10    $25.OO\n"
            "Widget 8eta                5    $42.5O\n"  # OCR: 8 for B
            "Service Fee                1    $1OO.OO\n\n"
            "Subtota1: $462.5O\n"
            "Tax (8%): $37.OO\n"
            "Tota1: $499.5O\n\n"
            "  \n"  # empty garbage line
            "~!@# OCR_NOISE_BLOCK &*() \n"  # pure artifact
            "|||///\\\\\\---\n"  # scan line artifact
        ),
        (
            "Payrnent Terms\n\n"  # OCR: rn for m
            "Payrnent is due within 3O days of invoice date.\n"
            "Late payrnents wi11 incur a 1.5% rnonthly fee.\n\n"
            "Bank Transfer Detai1s:\n"
            "Bank: First Nationa1 Bank\n"
            "Account: 1234-5678-9O12\n"
            "Routing: O11-O22-O33\n\n"
            "Please reference invoice #2847 in a11 correspondence.\n\n"
            "  __//==\\\\__  \n"  # scan artifact
            "Ã©Ã¨Ã¼Ã¶\n"  # broken UTF-8 encoding artifact
        ),
        (
            "Notes & Conditions\n\n"
            "A11 prices are in USD. Returns accepted within 14 days "
            "of de1ivery with original packaging.\n\n"
            "Warranty: 12 rnonths standard warranty on a11 products. "
            "Extended warranty avai1ab1e for purchase.\n\n"
            "Contact: support@exarnp1e.corn\n"
            "Phone: +1-555-O12-3456\n\n"
            "Thank you for your business!\n\n"
            "  .....:::::::.....\n"  # scan artifact
            "■□■□■□\n"  # garbled characters
        ),
    ]

    for i, body in enumerate(pages_content):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 30), header, fontsize=9, color=(0.4, 0.4, 0.4))
        page.insert_text(
            (50, 820), footer.format(n=i + 1), fontsize=9, color=(0.4, 0.4, 0.4)
        )
        rect = fitz.Rect(50, 60, 545, 790)
        page.insert_textbox(rect, body, fontsize=11, color=(0, 0, 0))

    doc.save(path)
    doc.close()


def create_sample_manual(path: str) -> None:
    """Technical manual with watermark + headers + some OCR artifacts."""
    doc = fitz.open()
    header = "Product Manual — Model X-200 Rev.3"
    footer = "© 2025 TechCo Industries — Page {n}"
    watermark = "CONFIDENTIAL"

    pages = [
        (
            "Chapter 1: Getting Started\n\n"
            "Thank you for purchasing the Mode1 X-2OO. This manual provides "
            "comprehensive instructions for insta11ation and operation.\n\n"
            "Safety Warnings:\n"
            "- Do not expose the device to ternperatures above 6O°C\n"
            "- Keep away frorn water and moisture\n"
            "- Disconnect power before servicing\n\n"
            "Package Contents:\n"
            "1. Mode1 X-2OO Main Unit\n"
            "2. Power Adapter (11OV/22OV)\n"
            "3. USB-C Cable\n"
            "4. Quick Start Guide"
        ),
        (
            "Chapter 2: Installation\n\n"
            "Step 1: P1ace the unit on a flat, stab1e surface.\n"
            "Step 2: Connect the power adapter to the rear pane1.\n"
            "Step 3: Press the power button for 3 seconds.\n"
            "Step 4: Fo11ow the on-screen setup wizard.\n\n"
            "Network Configuration:\n"
            "The device supports both Wi-Fi and Ethernet connections.\n"
            "For Wi-Fi: Navigate to Settings > Network > Wi-Fi\n"
            "For Ethernet: Connect an RJ-45 cab1e to the rear port."
        ),
        (
            "Chapter 3: Troubleshooting\n\n"
            "Prob1ern: Device does not power on\n"
            "So1ution: Check power connections and try a different out1et.\n\n"
            "Prob1ern: No network connectivity\n"
            "So1ution: Verify cab1e connections and router settings.\n\n"
            "Prob1ern: Display shows error code E-4O1\n"
            "So1ution: Perform a factory reset by ho1ding the reset "
            "button for 1O seconds.\n\n"
            "For additiona1 support, contact: support@techco.corn\n"
            "Phone: 1-8OO-TECHCO-1"
        ),
        (
            "Appendix A: Specifications\n\n"
            "Dimensions: 25Omm x 18Omm x 45mm\n"
            "Weight: 1.2kg\n"
            "Power: 11O-24OV AC, 5O/6OHz\n"
            "Operating Temp: O°C to 4O°C\n"
            "Storage Temp: -2O°C to 6O°C\n"
            "Connectivity: Wi-Fi 6, B1uetooth 5.O, Ethernet\n"
            "Certifications: FCC, CE, UL, RoHS\n\n"
            "Appendix B: Warranty\n\n"
            "This product is covered by a 24-rnonth 1irnited warranty "
            "from the date of purchase. See fu11 terms at "
            "www.techco.corn/warranty"
        ),
    ]

    for i, body in enumerate(pages):
        page = doc.new_page(width=595, height=842)

        # Watermark
        tw = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        fontsize = 54
        text_width = font.text_length(watermark, fontsize=fontsize)
        x = (page.rect.width - text_width) / 2
        y = page.rect.height / 2
        tw.append((x, y), watermark, font=font, fontsize=fontsize)
        tw.write_text(page, color=(0.9, 0.9, 0.9))

        # Header/Footer
        page.insert_text((50, 30), header, fontsize=9, color=(0.4, 0.4, 0.4))
        page.insert_text(
            (50, 820), footer.format(n=i + 1), fontsize=9, color=(0.4, 0.4, 0.4)
        )

        rect = fitz.Rect(50, 60, 545, 790)
        page.insert_textbox(rect, body, fontsize=11, color=(0, 0, 0))

    doc.save(path)
    doc.close()


if __name__ == "__main__":
    create_sample_report("samples/report_with_watermark.pdf")
    create_sample_ocr("samples/ocr_scanned_invoice.pdf")
    create_sample_manual("samples/manual_mixed_noise.pdf")
    print("Generated 3 sample PDFs in samples/")
