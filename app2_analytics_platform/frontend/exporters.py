"""Excel and PDF export helpers for App 2.

Excel via openpyxl (finance teams live in Excel — the JD lists it explicitly).
PDF via reportlab for report/dashboard export.
"""
from __future__ import annotations

import io

import pandas as pd


def to_excel(frames: dict[str, pd.DataFrame]) -> bytes:
    """Write one sheet per named DataFrame; return bytes for st.download_button."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        for sheet, df in frames.items():
            safe = (sheet or "Sheet")[:31]  # Excel sheet-name limit
            (df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)).to_excel(
                xl, sheet_name=safe, index=False)
    return buf.getvalue()


def report_to_pdf(title: str, body_markdown: str) -> bytes:
    """Render a simple, clean PDF from a markdown-ish report string."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm,
                            bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    styles = getSampleStyleSheet()
    h = ParagraphStyle("H", parent=styles["Heading1"], textColor=HexColor("#DB0011"))
    story = [Paragraph(title, h), Spacer(1, 0.4 * cm)]
    for line in body_markdown.splitlines():
        line = line.rstrip()
        if not line:
            story.append(Spacer(1, 0.2 * cm)); continue
        if line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith("- "):
            story.append(Paragraph("&bull; " + line[2:], styles["BodyText"]))
        else:
            story.append(Paragraph(line, styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()
