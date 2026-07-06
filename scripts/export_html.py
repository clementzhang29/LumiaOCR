"""Export OCR Markdown plus PDF page images to a readable HTML proof.

Usage:
  python scripts/export_html.py --pdf tests/file.pdf --markdown tests/file.result.md --out exports/file.html
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


def render_pdf_pages(pdf_path: Path, image_dir: Path, zoom: float = 1.6) -> list[Path]:
    import fitz

    image_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths: list[Path] = []
    try:
        matrix = fitz.Matrix(zoom, zoom)
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out = image_dir / f"page_{index:03d}.jpg"
            pix.save(out)
            image_paths.append(out)
    finally:
        doc.close()
    return image_paths


def extract_pdf_images(pdf_path: Path, image_dir: Path) -> list[dict]:
    import fitz

    image_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted: list[dict] = []
    seen = set()
    try:
        for page_index, page in enumerate(doc, start=1):
            for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                xref = image_info[0]
                if xref in seen:
                    continue
                seen.add(xref)
                data = doc.extract_image(xref)
                ext = data.get("ext", "png")
                width = int(data.get("width", 0) or image_info[2])
                height = int(data.get("height", 0) or image_info[3])
                if width < 80 or height < 80:
                    continue
                out = image_dir / f"page_{page_index:03d}_image_{image_index:02d}.{ext}"
                out.write_bytes(data["image"])
                extracted.append({"path": out, "page": page_index, "width": width, "height": height})
    finally:
        doc.close()
    return extracted


def rects_intersect(a, b) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def save_page_clip(page, bbox, out_path: Path, zoom: float = 2.0) -> None:
    import fitz

    rect = fitz.Rect(bbox)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_path)


def extract_table_items(page, page_index: int, table_dir: Path) -> list[dict]:
    items = []
    try:
        tables = page.find_tables().tables
    except Exception:
        tables = []

    for index, table in enumerate(tables, start=1):
        bbox = tuple(float(x) for x in table.bbox)
        rows = table.extract()
        crop_path = table_dir / f"page_{page_index:03d}_table_{index:02d}.png"
        save_page_clip(page, bbox, crop_path)
        items.append({
            "kind": "table",
            "page": page_index,
            "bbox": bbox,
            "rows": rows,
            "path": crop_path,
        })
    return items


def text_block_to_text(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        spans = [span.get("text", "") for span in line.get("spans", [])]
        line_text = "".join(spans).strip()
        if line_text:
            lines.append(line_text)
    return " ".join(lines).strip()


def classify_text_block(text: str) -> str:
    clean = text.strip()
    if not clean:
        return "empty"
    if re.match(r"^(Fig\.|Figure|Table)\s*\d+", clean, re.I):
        return "caption"
    if re.match(r"^[IVX]+\.\s+[A-Z][A-Z\s-]{3,}$", clean):
        return "h2"
    if re.match(r"^[A-Z][A-Z\s-]{5,}$", clean) and len(clean) < 90:
        return "h3"
    if len(clean) < 120 and clean.endswith(":"):
        return "h3"
    return "p"


def block_text_html(text: str) -> str:
    kind = classify_text_block(text)
    if kind == "caption":
        return f"<p class=\"caption-text\">{inline_markup(text)}</p>"
    if kind == "h2":
        return f"<h2>{inline_markup(text)}</h2>"
    if kind == "h3":
        return f"<h3>{inline_markup(text)}</h3>"
    return f"<p>{inline_markup(text)}</p>"


def table_item_html(item: dict, base: Path) -> str:
    rows = item.get("rows") or []
    cleaned_rows = []
    for row in rows:
        values = ["" if cell is None else str(cell).strip() for cell in row]
        if any(values):
            cleaned_rows.append(values)

    table_html = ""
    if cleaned_rows:
        header = cleaned_rows[0]
        body = cleaned_rows[1:]
        head_html = "".join(f"<th>{inline_markup(cell)}</th>" for cell in header)
        body_html = "\n".join(
            "<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in row) + "</tr>"
            for row in body
        )
        table_html = f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"

    crop = item.get("path")
    crop_html = ""
    if crop:
        crop_html = (
            f"<figure class=\"table-shot\"><img src=\"{html.escape(rel(crop, base))}\" "
            f"alt=\"Table screenshot\"><figcaption>Table screenshot from page {item['page']}</figcaption></figure>"
        )

    return f"""
    <section class="table-block">
      <h3>Table extracted from page {item['page']}</h3>
      {table_html}
      {crop_html}
    </section>
    """


def build_layout_article_html(pdf_path: Path, asset_dir: Path, base: Path) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    page_sections = []
    try:
        for page_index, page in enumerate(doc, start=1):
            page_asset_dir = asset_dir / "layout" / f"page_{page_index:03d}"
            page_asset_dir.mkdir(parents=True, exist_ok=True)
            table_items = extract_table_items(page, page_index, asset_dir / "tables")
            table_bboxes = [item["bbox"] for item in table_items]
            layout_items = table_items[:]

            image_count = 0
            for block in page.get_text("dict").get("blocks", []):
                bbox = tuple(float(x) for x in block.get("bbox", (0, 0, 0, 0)))
                if block.get("type") == 0:
                    if any(rects_intersect(bbox, table_bbox) for table_bbox in table_bboxes):
                        continue
                    text = text_block_to_text(block)
                    if text:
                        layout_items.append({"kind": "text", "bbox": bbox, "text": text, "page": page_index})
                elif block.get("type") == 1:
                    image = block.get("image")
                    width = int(block.get("width", 0))
                    height = int(block.get("height", 0))
                    if image and width >= 80 and height >= 80:
                        image_count += 1
                        ext = block.get("ext", "png")
                        out = page_asset_dir / f"image_{image_count:02d}.{ext}"
                        out.write_bytes(image)
                        layout_items.append({
                            "kind": "image",
                            "bbox": bbox,
                            "path": out,
                            "page": page_index,
                            "width": width,
                            "height": height,
                        })

            layout_items.sort(key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
            content = []
            for item in layout_items:
                if item["kind"] == "text":
                    content.append(block_text_html(item["text"]))
                elif item["kind"] == "image":
                    content.append(
                        f"""
                        <figure class="inline-figure">
                          <img src="{html.escape(rel(item['path'], base))}" alt="Figure from page {item['page']}">
                          <figcaption>Figure from page {item['page']} ({item['width']} x {item['height']})</figcaption>
                        </figure>
                        """
                    )
                elif item["kind"] == "table":
                    content.append(table_item_html(item, base))

            page_sections.append(
                f"""
                <section class="layout-page" id="reflow-page-{page_index}">
                  <div class="page-marker">Page {page_index}</div>
                  {''.join(content)}
                </section>
                """
            )
    finally:
        doc.close()
    return "\n".join(page_sections)


def markdown_to_html(markdown: str, figures_html: str = "") -> str:
    markdown = normalize_scientific_markdown(markdown)
    blocks = re.split(r"\n{2,}", markdown.strip())
    html_blocks: list[str] = []
    inserted_figures = False

    for block in blocks:
        text = block.strip()
        if not text:
            continue
        if text.startswith("```"):
            content = text.strip("`").strip()
            html_blocks.append(f"<pre><code>{html.escape(content)}</code></pre>")
        elif text.startswith("$$") and text.endswith("$$"):
            formula = text.strip("$").strip()
            html_blocks.append(f"<div class=\"formula\">{html.escape(formula)}</div>")
        elif re.match(r"^#{1,6}\s", text):
            level = min(len(text) - len(text.lstrip("#")), 4)
            content = text.lstrip("#").strip()
            html_blocks.append(f"<h{level}>{inline_markup(content)}</h{level}>")
            if figures_html and not inserted_figures and re.search(r"\bINTRODUCTION\b|\bLITERATURE\b", content, re.I):
                html_blocks.append(figures_html)
                inserted_figures = True
        elif looks_like_table(text):
            html_blocks.append(table_to_html(text))
        elif all(line.lstrip().startswith(("- ", "* ")) for line in text.splitlines() if line.strip()):
            items = "\n".join(
                f"<li>{inline_markup(line.strip()[2:].strip())}</li>"
                for line in text.splitlines()
                if line.strip()
            )
            html_blocks.append(f"<ul>{items}</ul>")
        else:
            paragraph = " ".join(line.strip() for line in text.splitlines())
            html_blocks.append(f"<p>{inline_markup(paragraph)}</p>")

    if figures_html and not inserted_figures:
        html_blocks.append(figures_html)
    return "\n".join(html_blocks)


def normalize_scientific_markdown(markdown: str) -> str:
    text = markdown.replace("\ufeff", "")
    text = re.sub(r"(?m)^#\s+#\s+", "# ", text)
    text = re.sub(r"(?<!\n)(#{2,4})\s*(?=[A-Z])", r"\n\n\1 ", text)
    text = re.sub(r"(?m)^(#{1,4}\s+[IVX]+\.\s+[A-Z][A-Z ]{3,})([A-Z][a-z])", r"\1\n\n\2", text)
    text = re.sub(r"(?i)([a-z0-9)])(Abstract\s*[-:])", r"\1\n\n## Abstract\n\n", text)
    text = re.sub(r"(?i)(\bAbstract\s*[-:])", "## Abstract\n\n", text, count=1)
    text = re.sub(r"(?m)^(# .{120,}?)(## .+)$", r"\1\n\n\2", text)
    lines = []
    for line in text.splitlines():
        if re.match(r"^#{1,4}\s", line) and len(line) > 120:
            split_at = find_heading_split(line)
            if split_at:
                lines.append(line[:split_at].strip())
                lines.append("")
                lines.append(line[split_at:].strip())
            else:
                lines.append(line)
        else:
            lines.append(line)
    return "\n".join(lines)


def find_heading_split(line: str) -> int | None:
    candidates = ["## ", "Department", "Abstract", "Retrieving", "This document", "In today's"]
    positions = [line.find(token) for token in candidates if line.find(token) > 30]
    return min(positions) if positions else None


def inline_markup(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\$([^$\n]+)\$", r"<span class=\"inline-formula\">\1</span>", safe)
    return safe


def looks_like_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return len(lines) >= 2 and all(line.startswith("|") and line.endswith("|") for line in lines)


def table_to_html(text: str) -> str:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(re.match(r"^:?-{3,}:?$", cell) for cell in cells):
            continue
        rows.append(cells)

    if not rows:
        return ""

    header = rows[0]
    body = rows[1:]
    head_html = "".join(f"<th>{inline_markup(cell)}</th>" for cell in header)
    body_html = "\n".join(
        "<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in row) + "</tr>"
        for row in body
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def build_figures_html(extracted_images: list[dict], base: Path) -> str:
    if not extracted_images:
        return ""
    cards = []
    for index, item in enumerate(extracted_images, start=1):
        path = item["path"]
        page = item["page"]
        width = item["width"]
        height = item["height"]
        cards.append(
            f"""
            <figure class="extracted-figure">
              <img src="{html.escape(rel(path, base))}" alt="Extracted figure {index}">
              <figcaption>Figure {index}, extracted from page {page} ({width} x {height})</figcaption>
            </figure>
            """
        )
    return f"""
    <section class="figures-section">
      <h2>Extracted Figures</h2>
      <p>Images embedded in the source PDF are extracted and loaded here for the reflowed reading view.</p>
      <div class="figure-grid">{''.join(cards)}</div>
    </section>
    """


def build_html(pdf_path: Path, markdown_path: Path, out_path: Path, title: str) -> None:
    asset_dir = out_path.parent / f"{out_path.stem}_assets"
    page_paths = render_pdf_pages(pdf_path, asset_dir / "pages")
    markdown = markdown_path.read_text(encoding="utf-8-sig")
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        from src.formatter import MarkdownCleaner

        markdown = MarkdownCleaner().clean(markdown)
    except Exception:
        pass
    layout_body_html = build_layout_article_html(pdf_path, asset_dir, out_path.parent)
    markdown_body_html = markdown_to_html(markdown)
    body_html = f"""
    <div class="mode-note">Layout-aware reconstruction: text, tables, and figures are ordered from PDF page geometry. OCR Markdown is kept as a reference appendix below.</div>
    {layout_body_html}
    <details class="ocr-appendix">
      <summary>OCR Markdown reference</summary>
      <div class="ocr-reference">{markdown_body_html}</div>
    </details>
    """
    pages_html = "\n".join(
        f"""
        <figure class="page-card">
          <img src="{html.escape(rel(path, out_path.parent))}" alt="Page {idx}">
          <figcaption>Page {idx}</figcaption>
        </figure>
        """
        for idx, path in enumerate(page_paths, start=1)
    )

    source_name = html.escape(pdf_path.name)
    title_html = html.escape(title)
    payload = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_html}</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #66758f;
      --line: #dbe3ef;
      --paper: #ffffff;
      --soft: #f5f7fb;
      --accent: #335cff;
      --teal: #0f9f8f;
      --cream: #fffaf0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, "Noto Sans", sans-serif;
      color: var(--ink);
      background: #f6f8fc;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 5;
      padding: 16px 28px;
      background: rgba(255, 255, 255, 0.9);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(14px);
    }}
    header h1 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    header p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    main {{
      max-width: 1560px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: minmax(330px, 0.66fr) minmax(620px, 1.34fr);
      gap: 18px;
      align-items: start;
    }}
    .pane {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,0.96);
      box-shadow: 0 18px 45px rgba(23, 32, 51, 0.08);
      overflow: hidden;
    }}
    .pane-title {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--paper);
      font-weight: 800;
    }}
    .badge {{
      color: #08756a;
      background: #e4f7f4;
      padding: 5px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 800;
    }}
    .pages {{
      padding: 14px;
      display: grid;
      gap: 14px;
      max-height: calc(100vh - 118px);
      overflow: auto;
    }}
    .page-card {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      padding: 10px;
    }}
    .page-card img {{
      width: 100%;
      display: block;
      border-radius: 6px;
      background: white;
    }}
    figcaption {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 7px;
      text-align: center;
    }}
    article {{
      padding: 38px 54px;
      max-height: calc(100vh - 118px);
      overflow: auto;
      font-family: Georgia, "Times New Roman", "Noto Serif", serif;
      font-size: 15.5px;
      line-height: 1.58;
      background:
        linear-gradient(90deg, transparent 0, transparent 72px, rgba(219,227,239,.75) 72px, rgba(219,227,239,.75) 73px, transparent 73px),
        #fff;
    }}
    article h1, article h2, article h3, article h4 {{
      line-height: 1.32;
      letter-spacing: 0;
      margin: 1.2em 0 0.45em;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }}
    article h1 {{
      max-width: 820px;
      margin-left: auto;
      margin-right: auto;
      font-size: 30px;
      text-align: center;
    }}
    article h2 {{
      font-size: 18px;
      border-top: 1px solid var(--line);
      padding-top: 14px;
      text-transform: uppercase;
    }}
    article h3 {{
      font-size: 15px;
      color: var(--accent);
    }}
    article h1:first-child, article h2:first-child {{
      margin-top: 0;
    }}
    article p {{
      margin: 0.72em 0;
      text-align: justify;
      hyphens: auto;
    }}
    .mode-note {{
      margin: 0 0 18px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #eef7ff;
      border: 1px solid #c9e3ff;
      color: #315878;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      font-size: 12px;
      line-height: 1.45;
    }}
    .layout-page {{
      margin: 0 0 26px;
      padding-bottom: 22px;
      border-bottom: 1px solid var(--line);
      column-count: 2;
      column-gap: 34px;
    }}
    .layout-page:first-of-type {{
      column-count: 1;
    }}
    .page-marker {{
      column-span: all;
      margin: 0 0 12px;
      color: var(--muted);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .layout-page h2,
    .layout-page h3,
    .layout-page table,
    .layout-page .inline-figure,
    .layout-page .table-block {{
      break-inside: avoid;
    }}
    .caption-text {{
      color: #44536b;
      font-size: 12.5px;
      text-align: center;
      font-style: italic;
    }}
    .figures-section {{
      margin: 26px 0;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--cream);
    }}
    .figures-section h2 {{
      border-top: 0;
      padding-top: 0;
      margin-top: 0;
    }}
    .figure-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .extracted-figure {{
      margin: 0;
      border: 1px solid #eadcbf;
      border-radius: 8px;
      background: white;
      padding: 10px;
    }}
    .extracted-figure img {{
      width: 100%;
      display: block;
      border-radius: 6px;
      object-fit: contain;
    }}
    .inline-figure {{
      margin: 14px 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      break-inside: avoid;
    }}
    .inline-figure img {{
      display: block;
      max-width: 100%;
      margin: 0 auto;
      border-radius: 6px;
    }}
    .table-block {{
      column-span: all;
      margin: 18px 0;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      break-inside: avoid;
    }}
    .table-block h3 {{
      margin-top: 0;
    }}
    .table-shot {{
      margin: 12px 0 0;
      padding: 8px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: white;
    }}
    .table-shot img {{
      display: block;
      max-width: 100%;
      margin: 0 auto;
      border-radius: 6px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .ocr-appendix {{
      margin-top: 24px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fafcff;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }}
    .ocr-appendix summary {{
      cursor: pointer;
      font-weight: 800;
    }}
    .ocr-reference {{
      margin-top: 14px;
      font-family: Georgia, "Times New Roman", "Noto Serif", serif;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #eef3ff;
      font-weight: 800;
    }}
    .formula {{
      margin: 16px 0;
      padding: 12px 14px;
      overflow-x: auto;
      border-radius: 8px;
      background: #111827;
      color: #e5e7eb;
      font-family: "Cascadia Mono", Consolas, monospace;
      white-space: pre-wrap;
    }}
    .inline-formula, code {{
      background: #edf2ff;
      border-radius: 5px;
      padding: 1px 4px;
      font-family: "Cascadia Mono", Consolas, monospace;
    }}
    pre {{
      overflow: auto;
      padding: 14px;
      border-radius: 8px;
      background: #111827;
      color: #e5e7eb;
    }}
    @media (max-width: 980px) {{
      main {{
        grid-template-columns: 1fr;
        padding: 14px;
      }}
      .pages, article {{
        max-height: none;
      }}
      article {{
        padding: 24px;
      }}
      .layout-page {{
        column-count: 1;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title_html}</h1>
    <p>Source PDF: {source_name}. Left pane keeps page images; right pane is OCR text reflowed into readable HTML.</p>
  </header>
  <main>
    <section class="pane">
      <div class="pane-title">Original Pages <span class="badge">{len(page_paths)} pages</span></div>
      <div class="pages">{pages_html}</div>
    </section>
    <section class="pane">
      <div class="pane-title">Reflowed OCR HTML <span class="badge">Markdown based</span></div>
      <article>{body_html}</article>
    </section>
  </main>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--title", default="OCR HTML Proof")
    args = parser.parse_args()
    build_html(args.pdf, args.markdown, args.out, args.title)
    print(args.out.resolve())


if __name__ == "__main__":
    main()
