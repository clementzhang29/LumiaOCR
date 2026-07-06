"""
文档分析器 — 自动检测文档类型，为路由决策提供依据。
"""
import os


class DocumentAnalyzer:
    """分析 PDF 文档特征，判断文档类型和最佳处理策略"""

    async def analyze(self, pdf_path: str) -> dict:
        """返回文档分析结果"""
        result = {
            "file_size": os.path.getsize(pdf_path),
            "page_count": 0,
            "has_text_layer": False,
            "doc_type": "unknown",
            "language_hint": "unknown",
            "has_formulas": False,
            "has_tables": False,
            "has_images": False,
            "is_scanned": False,
            "recommended_engine": "mineru",
        }
        try:
            import fitz
            doc = fitz.open(pdf_path)
            result["page_count"] = len(doc)

            text_samples = 0
            image_count = 0
            for i in range(min(len(doc), 5)):
                page = doc[i]
                text = page.get_text().strip()
                if len(text) > 50:
                    text_samples += 1
                image_count += len(page.get_images())

            result["has_text_layer"] = text_samples >= 3
            result["is_scanned"] = not result["has_text_layer"]
            result["has_images"] = image_count > 3
            result["has_tables"] = self._detect_tables(doc)
            result["has_formulas"] = self._detect_formulas(doc)
            result["language_hint"] = self._detect_language(doc)
            result["doc_type"] = self._classify_document(result)
            result["recommended_engine"] = self._recommend_engine(result)
            doc.close()
        except ImportError:
            pass
        except Exception:
            pass
        return result

    def _detect_tables(self, doc) -> bool:
        try:
            for i in range(min(len(doc), 3)):
                page = doc[i]
                text = page.get_text()
                if text.count("|") > 5:
                    return True
            return False
        except Exception:
            return False

    def _detect_formulas(self, doc) -> bool:
        try:
            import re
            for i in range(min(len(doc), 3)):
                page = doc[i]
                text = page.get_text()
                if re.search(r"[\[\]\(\)\{\}\=\+\-\*\/\\sum\\int\\alpha\\beta]", text):
                    return True
            return False
        except Exception:
            return False

    def _detect_language(self, doc) -> str:
        try:
            text = ""
            for i in range(min(len(doc), 3)):
                text += doc[i].get_text()
            chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            if chinese_chars > len(text) * 0.05:
                return "zh"
            return "en"
        except Exception:
            return "en"

    def _classify_document(self, info: dict) -> str:
        if info["is_scanned"] and info["has_images"]:
            return "scanned_book"
        elif info["has_formulas"] and (info["has_images"] or info["has_tables"]):
            return "complex_scientific_paper"
        elif info["has_formulas"]:
            return "scientific_paper"
        elif info["has_tables"] and not info["is_scanned"]:
            return "report"
        elif info["is_scanned"]:
            return "scanned_document"
        return "digital_document"

    def _recommend_engine(self, info: dict) -> str:
        mapping = {
            "scanned_book": "mineru",
            "complex_scientific_paper": "dolphin",
            "scientific_paper": "dolphin",
            "scanned_document": "marker",
            "report": "mineru",
            "digital_document": "marker",
        }
        lang_boost = "paddleocr" if info["language_hint"] == "zh" else None
        return mapping.get(info["doc_type"], "mineru")
