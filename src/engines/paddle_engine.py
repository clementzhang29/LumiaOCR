from .base import BaseEngine, OCRResult
import time
import tempfile
from pathlib import Path


class PaddleOCREngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "PaddleOCR"
        self._ocr = None
        self._uses_new_api = False

    def _get_ocr(self):
        import os
        from paddleocr import PaddleOCR

        if self._ocr is not None:
            return self._ocr

        lang = self.config.get("lang", "ch")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        try:
            self._ocr = PaddleOCR(
                lang=lang,
                ocr_version=self.config.get("ocr_version", "PP-OCRv4"),
                use_textline_orientation=True,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
            self._uses_new_api = True
        except (TypeError, ValueError):
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=self.config.get("gpu", True),
            )
            self._uses_new_api = False
        return self._ocr

    def _extract_text(self, result) -> list[str]:
        if not result:
            return []

        lines: list[str] = []
        for page in result:
            if isinstance(page, dict):
                rec_texts = page.get("rec_texts") or page.get("text") or []
                if isinstance(rec_texts, str):
                    lines.append(rec_texts)
                else:
                    lines.extend(str(text) for text in rec_texts if text)
                continue
            if hasattr(page, "json"):
                page_json = page.json() if callable(page.json) else page.json
                if isinstance(page_json, dict):
                    rec_texts = page_json.get("rec_texts") or page_json.get("text") or []
                    if isinstance(rec_texts, str):
                        lines.append(rec_texts)
                    else:
                        lines.extend(str(text) for text in rec_texts if text)
                    continue
            if isinstance(page, list):
                for line in page:
                    try:
                        lines.append(line[1][0])
                    except (IndexError, TypeError):
                        pass
        return lines

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        try:
            ocr = self._get_ocr()
            import fitz
            doc = fitz.open(pdf_path)
            full_text = []
            with tempfile.TemporaryDirectory(prefix="paddleocr_") as temp_dir:
                temp_path = Path(temp_dir)
                for page_num in range(len(doc)):
                    pix = doc[page_num].get_pixmap(dpi=300)
                    img_path = temp_path / f"page_{page_num}.png"
                    pix.save(str(img_path))
                    if self._uses_new_api:
                        result = ocr.ocr(str(img_path))
                    else:
                        result = ocr.ocr(str(img_path), cls=True)
                    full_text.extend(self._extract_text(result))
            doc.close()
            return OCRResult(markdown="\n\n".join(full_text), engine=self.name, processing_time=time.time() - start)
        except ImportError:
            return OCRResult(success=False, error="PaddleOCR not installed. Run: pip install paddleocr", engine=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), engine=self.name, processing_time=time.time() - start)

    async def is_available(self) -> bool:
        try:
            import paddleocr
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {"name": "PaddleOCR", "gpu": self.config.get("gpu", True), "lang": self.config.get("lang", "ch")}
