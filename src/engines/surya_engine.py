"""Surya OCR 引擎封装 (兼容 surya-ocr 0.17.x)。"""
from .base import BaseEngine, OCRResult
import time


class SuryaEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "Surya"
        self._foundation = None
        self._det_predictor = None
        self._rec_predictor = None

    def _ensure_models(self):
        """懒加载 Surya 模型。"""
        if self._rec_predictor is not None:
            return
        from surya.foundation import FoundationPredictor
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor
        import torch
        device = "cuda" if torch.cuda.is_available() and self.config.get("gpu", True) else "cpu"
        self._foundation = FoundationPredictor(device=device)
        self._det_predictor = DetectionPredictor(device=device)
        self._rec_predictor = RecognitionPredictor(self._foundation)

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        try:
            from surya.common.surya.schema import TaskNames
            from PIL import Image
            import fitz
        except ImportError:
            return OCRResult(
                success=False,
                error="Surya not installed. Run: pip install surya-ocr",
                engine=self.name,
            )

        try:
            self._ensure_models()
            doc = fitz.open(pdf_path)
            images: list[Image.Image] = []
            for i in range(len(doc)):
                pix = doc[i].get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            doc.close()

            task_names = [TaskNames.ocr_with_boxes] * len(images)
            predictions = self._rec_predictor(
                images,
                task_names=task_names,
                det_predictor=self._det_predictor,
                highres_images=images,
                math_mode=False,
            )

            full_text: list[str] = []
            for pred in predictions:
                page_lines = [line.text for line in pred.text_lines]
                full_text.append("\n".join(page_lines))
            markdown = "\n\n".join(full_text)
            return OCRResult(
                markdown=markdown,
                engine=self.name,
                processing_time=time.time() - start,
            )
        except Exception as e:
            return OCRResult(
                success=False,
                error=str(e),
                engine=self.name,
                processing_time=time.time() - start,
            )

    async def is_available(self) -> bool:
        try:
            import surya.foundation  # noqa: F401
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {
            "name": "Surya",
            "gpu": self.config.get("gpu", True),
            "lang": self.config.get("lang", "zh,en"),
        }
