"""生成测试 PDF：用 reportlab 创建带文字 + 简单表格的多页 PDF。"""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


def find_cjk_font() -> str:
    candidates = [
        r"C:\\Windows\\Fonts\\msyh.ttc",
        r"C:\\Windows\\Fonts\\simsun.ttc",
        r"C:\\Windows\\Fonts\\msyh.ttf",
        r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "Helvetica"


def build(path: Path) -> None:
    font = find_cjk_font()
    try:
        if font.endswith(".ttc"):
            pdfmetrics.registerFont(TTFont("body", font, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont("body", font))
        body = "body"
    except Exception:
        body = "Helvetica"

    c = Canvas(str(path), pagesize=A4)
    width, height = A4

    c.setFont(body, 18)
    c.drawString(2 * cm, height - 2 * cm, "OCR-Harness Test Sample")
    c.setFont(body, 11)
    c.drawString(2 * cm, height - 3 * cm, "Document for end-to-end OCR benchmarking.")

    body_text = [
        "Section 1: Introduction",
        "This is a sample document used to verify OCR pipelines.",
        "It contains plain text paragraphs, a simple table, and a math formula.",
        "",
        "Section 2: Table",
        "Item | Qty | Price",
        "Apple | 4 | $5",
        "Bread | 2 | $3",
        "",
        "Section 3: Formula",
        "Euler's identity: e^(i*pi) + 1 = 0",
        "Quadratic equation: x = (-b +/- sqrt(b^2 - 4ac)) / (2a)",
    ]
    y = height - 5 * cm
    for line in body_text:
        c.setFont(body, 11)
        c.drawString(2 * cm, y, line)
        y -= 0.6 * cm

    c.showPage()
    c.setFont(body, 14)
    c.drawString(2 * cm, height - 2 * cm, "Page 2: additional notes")
    c.setFont(body, 11)
    notes = [
        "OCR-Harness integrates 6 engines (MinerU, Marker, Docling,",
        "PaddleOCR, Nougat, Surya) with LLM-based correction.",
        "Quality scoring auto-triggers fallback engines when",
        "the produced Markdown scores below 0.85.",
    ]
    y = height - 4 * cm
    for line in notes:
        c.drawString(2 * cm, y, line)
        y -= 0.6 * cm

    c.save()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "test_sample.pdf"
    build(out)
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
