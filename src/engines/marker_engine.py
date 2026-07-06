from .base import BaseEngine, OCRResult
import time


class MarkerEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "Marker"

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        try:
            try:
                from marker.convert import convert_single_pdf
            except ImportError:
                convert_single_pdf = None

            if convert_single_pdf:
                markdown, metadata = convert_single_pdf(pdf_path, **kwargs)
                return OCRResult(
                    markdown=markdown,
                    metadata=metadata,
                    engine=self.name,
                    processing_time=time.time() - start,
                )

            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
            import torch

            device = "cuda" if torch.cuda.is_available() and self.config.get("gpu", True) else "cpu"
            converter = PdfConverter(
                artifact_dict=create_model_dict(device=device),
                config=kwargs or None,
            )
            rendered = converter(pdf_path)
            markdown, output_format, images = text_from_rendered(rendered)
            metadata = getattr(rendered, "metadata", {}) or {}
            metadata["output_format"] = output_format
            metadata["image_count"] = len(images or {})
            return OCRResult(
                markdown=markdown,
                metadata=metadata,
                engine=self.name,
                processing_time=time.time() - start,
            )
        except ImportError as exc:
            return OCRResult(success=False, error="Marker not installed. Run: pip install marker-pdf", engine=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), engine=self.name, processing_time=time.time() - start)

    async def is_available(self) -> bool:
        try:
            import marker
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {"name": "Marker", "gpu": self.config.get("gpu", True), "lang": "multi"}
