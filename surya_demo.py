"""Surya OCR real-time demo system - Streamlit desktop UI."""
import os, sys, time, json, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Surya OCR Real-time Demo", page_icon="pdf", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { text-align: center; padding: 0.5rem 0; }
    .main-header h1 { font-size: 2rem; margin-bottom: 0.2rem; }
    .main-header p { color: #666; font-size: 1rem; }
    .metric-card { background: #f0f2f6; border-radius: 12px; padding: 16px; text-align: center; }
    .metric-card .value { font-size: 28px; font-weight: 700; color: #1f77b4; }
    .metric-card .label { font-size: 13px; color: #666; margin-top: 4px; }
    .stProgress > div > div > div > div { background-color: #1f77b4; }
    p, span, div, label { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", sans-serif; }
</style>
""", unsafe_allow_html=True)

SKEYS = ["ocr_running", "ocr_done", "results", "page_times", "page_texts",
         "pdf_images", "total_pages", "det_predictor", "rec_predictor", "foundation"]
for k in SKEYS:
    if k not in st.session_state:
        if k in ("ocr_running", "ocr_done"):
            st.session_state[k] = False
        elif k == "total_pages":
            st.session_state[k] = 0
        else:
            st.session_state[k] = {} if k == "results" else []

def ensure_models(device):
    if st.session_state.det_predictor is not None:
        return
    from surya.foundation import FoundationPredictor
    from surya.detection import DetectionPredictor
    from surya.recognition import RecognitionPredictor
    st.session_state.foundation = FoundationPredictor(device=device)
    st.session_state.det_predictor = DetectionPredictor(device=device)
    st.session_state.rec_predictor = RecognitionPredictor(st.session_state.foundation)

def draw_boxes(image, det_result, color="#00FF00"):
    img = image.copy()
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    if hasattr(det_result, "bboxes"):
        for i, bbox in enumerate(det_result.bboxes):
            x1, y1, x2, y2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
    elif hasattr(det_result, "polygons"):
        for i, poly in enumerate(det_result.polygons):
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=color, width=2)
    elif hasattr(det_result, "text_lines"):
        for line in det_result.text_lines:
            if hasattr(line, "bbox"):
                x1, y1, x2, y2 = line.bbox
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
    return img

# ---- Sidebar ----
with st.sidebar:
    st.markdown("## Configuration")
    use_gpu = st.checkbox("Use GPU (CUDA)", value=True, disabled=True, help="No CUDA GPU detected, using CPU")
    uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])

    st.markdown("---")
    st.markdown("### System Info")
    import torch
    cuda = torch.cuda.is_available()
    st.markdown(f"- **PyTorch**: {torch.__version__}")
    st.markdown(f"- **CUDA**: {'Available' if cuda else 'CPU mode'}")
    from surya.settings import settings
    st.markdown(f"- **Model cache**: `{settings.MODEL_CACHE_DIR}`")
    base = settings.MODEL_CACHE_DIR
    cache_models = []
    for m in ["text_detection", "text_recognition", "layout", "ocr_error_detection", "table_recognition"]:
        p = os.path.join(base, m)
        if os.path.exists(p):
            subs = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
            cache_models.append(f"{m} ({', '.join(subs)})")
    st.markdown(f"- **Cached models**: {len(cache_models)}")
    for cm in cache_models:
        st.markdown(f"  - {cm}")

# ---- Main ----
st.markdown('<div class="main-header"><h1>PDF OCR with Surya</h1><p>Surya 0.17.x - 90+ languages - Real-time page-by-page preview with detection boxes</p></div>', unsafe_allow_html=True)

if uploaded_file is not None and not st.session_state.ocr_running and not st.session_state.ocr_done:
    if st.button("Start OCR Conversion", type="primary", use_container_width=True):
        st.session_state.ocr_running = True
        st.session_state.ocr_done = False
        st.session_state.page_texts = []
        st.session_state.page_times = []
        st.session_state.pdf_images = []

        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        col_prog, col_stat = st.columns([3, 1])
        with col_prog:
            progress_bar = st.progress(0, text="Initializing...")
        with col_stat:
            status_text = st.empty()

        device = "cpu"
        with st.spinner("Loading Surya models..."):
            ensure_models(device)
        status_text.metric("Model", "Loaded")

        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(temp_path)
        total_pages = len(pdf)
        st.session_state.total_pages = total_pages
        progress_bar.progress(5, text=f"PDF loaded: {total_pages} pages")

        all_texts, all_times, all_imgs = [], [], []
        t_start = time.time()

        for page_idx in range(total_pages):
            pct = 5 + int((page_idx + 1) / total_pages * 85)
            status_text.metric("Page", f"{page_idx+1}/{total_pages}")

            pg = pdf[page_idx]
            bitmap = pg.render(scale=200 / 72)
            pil_img = bitmap.to_pil()

            progress_bar.progress(pct, text=f"Page {page_idx+1}/{total_pages}: detecting text regions...")
            det_result = st.session_state.det_predictor([pil_img])[0]
            boxed_img = draw_boxes(pil_img, det_result)

            progress_bar.progress(pct + 3, text=f"Page {page_idx+1}/{total_pages}: recognizing text...")
            t_page = time.time()
            pred = st.session_state.rec_predictor([pil_img], det_predictor=st.session_state.det_predictor)

            page_text = ""
            if pred and hasattr(pred[0], "text_lines"):
                lines = [ln.text for ln in pred[0].text_lines if ln.text]
                page_text = "\n".join(lines)

            page_elapsed = time.time() - t_page
            all_texts.append(page_text)
            all_times.append(page_elapsed)
            all_imgs.append(boxed_img)

            elapsed = time.time() - t_start
            progress_bar.progress(pct + 6, text=f"Page {page_idx+1}/{total_pages} done ({page_elapsed:.1f}s) | Total {elapsed:.0f}s")

        pdf.close()
        total_time = time.time() - t_start

        st.session_state.page_texts = all_texts
        st.session_state.page_times = all_times
        st.session_state.pdf_images = all_imgs
        st.session_state.results = {"total_pages": total_pages, "total_time": total_time, "device_used": "CPU"}

        progress_bar.empty()
        status_text.empty()
        st.session_state.ocr_running = False
        st.session_state.ocr_done = True
        st.rerun()

if st.session_state.ocr_done:
    total_pages = st.session_state.total_pages
    page_texts = st.session_state.page_texts
    page_times = st.session_state.page_times
    pdf_images = st.session_state.pdf_images
    total_time = st.session_state.results["total_time"]

    avg_time = sum(page_times) / len(page_times) if page_times else 0
    total_chars = sum(len(t) for t in page_texts)
    cps = total_chars / total_time if total_time > 0 else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="value">{total_pages}</div><div class="label">Pages</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="value">{total_time:.1f}s</div><div class="label">Total time</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="value">{avg_time:.2f}s</div><div class="label">Avg per page</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="value">{total_chars}</div><div class="label">Characters</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="metric-card"><div class="value">{cps:.0f}</div><div class="label">Chars/sec</div></div>', unsafe_allow_html=True)

    st.info(f"Surya 0.17.x | Device: CPU | {total_pages} pages | Avg {avg_time:.2f}s/page")

    st.markdown("### Page-by-page comparison")
    page_idx = 0
    if total_pages > 1:
        page_num = st.selectbox("Select page", options=list(range(1, total_pages+1)), format_func=lambda x: f"Page {x}", key="pager")
        page_idx = page_num - 1

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Detection boxes**")
        if page_idx < len(pdf_images):
            st.image(pdf_images[page_idx], use_container_width=True)
    with col_right:
        st.markdown("**OCR text**")
        if page_idx < len(page_texts):
            text = page_texts[page_idx] or "(No text detected)"
            st.text_area("", text, height=520, label_visibility="collapsed")
            st.caption(f"{page_times[page_idx]:.2f}s | {len(text)} chars")
        if page_idx < len(page_texts):
            st.download_button("Download page", page_texts[page_idx], file_name=f"page_{page_idx+1}.txt", use_container_width=True)

    st.markdown("---")
    st.markdown("### Performance per page")
    c1, c2 = st.columns(2)
    with c1:
        df1 = pd.DataFrame({"Page": [f"P{i+1}" for i in range(total_pages)], "Time(s)": page_times})
        st.bar_chart(df1, x="Page", y="Time(s)", use_container_width=True)
    with c2:
        df2 = pd.DataFrame({"Page": [f"P{i+1}" for i in range(total_pages)], "Chars": [len(t) for t in page_texts]})
        st.bar_chart(df2, x="Page", y="Chars", use_container_width=True)

    with st.expander("Full result"):
        full = "\n\n".join([f"--- Page {i+1} ---\n{t}" for i, t in enumerate(page_texts)])
        st.text_area("", full, height=300, label_visibility="collapsed")
        st.download_button("Download all (Markdown)", full, file_name=f"surya_ocr_{time.strftime('%Y%m%d_%H%M%S')}.md", mime="text/markdown", use_container_width=True)

    if st.button("Start over", use_container_width=True):
        for k in SKEYS:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

elif uploaded_file is None:
    st.info("Upload a PDF file in the sidebar, then click Start OCR Conversion")
