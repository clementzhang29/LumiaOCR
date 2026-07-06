from .base import BaseEngine, OCRResult
import time


class DoclingEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "Docling"

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            markdown = result.document.export_to_markdown()
            return OCRResult(markdown=markdown, engine=self.name, processing_time=time.time() - start)
        except ImportError:
            return OCRResult(success=False, error="Docling not installed. Run: pip install docling", engine=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), engine=self.name, processing_time=time.time() - start)

    async def is_available(self) -> bool:
        try:
            import docling
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {"name": "Docling", "gpu": self.config.get("gpu", True), "lang": "multi"}