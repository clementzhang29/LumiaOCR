"""
Pipeline 编排核心 — 智能调度、执行、修正、质量评估。
"""
import asyncio
import time
import logging
from typing import Optional
from ..engines import BaseEngine, OCRResult
from ..correctors import TableCorrector, FormulaCorrector, OrderingCorrector
from ..qa import QualityScorer
from ..formatter import MarkdownCleaner

logger = logging.getLogger(__name__)


class OCRPipeline:
    def __init__(self, engines: dict[str, BaseEngine], llm_router=None):
        self.engines = engines
        self.llm_router = llm_router
        self.table_corrector = TableCorrector()
        self.formula_corrector = FormulaCorrector()
        self.ordering_corrector = OrderingCorrector()
        self.scorer = QualityScorer()
        self.cleaner = MarkdownCleaner()

    async def run(self, pdf_path: str, strategy: str = "auto", preferred_engine: str = "") -> dict:
        start = time.time()
        result = {
            "markdown": "",
            "quality_score": 0,
            "processing_time": 0,
            "engine_used": "",
            "corrections": [],
            "output_profile": self.cleaner.profile(),
            "status": "pending",
        }

        primary_result = await self._execute_primary(pdf_path, strategy, preferred_engine)
        if not primary_result.success:
            result["status"] = "failed"
            result["error"] = primary_result.error
            return result

        result["markdown"] = primary_result.markdown
        result["engine_used"] = primary_result.engine
        markdown = primary_result.markdown

        # Step 2: 校正管道（LLM 异常时静默回退规则修复）
        try:
            markdown, corrections = await self._correction_pipeline(markdown)
        except Exception as exc:
            logger.warning("Correction pipeline failed, falling back: %s", exc)
            corrections = []
        result["corrections"] = corrections

        # Step 3: 质量评分
        quality = await self.scorer.score(markdown)
        result["quality_score"] = quality["total"]
        result["quality_details"] = quality

        # Step 4: 如果质量不合格，尝试用其他引擎补充修正
        if not quality["passed"] and strategy != "single":
            try:
                fallback_result = await self._fallback_correction(pdf_path, markdown, quality)
                if fallback_result:
                    markdown = fallback_result["markdown"]
                    result["corrections"].extend(fallback_result["corrections"])
                    quality = await self.scorer.score(markdown)
                    result["quality_score"] = quality["total"]
                    result["quality_details"] = quality
            except Exception as exc:
                logger.warning("Fallback correction failed: %s", exc)

        # Step 5: 格式化美化
        markdown = self.cleaner.clean(markdown)
        result["markdown"] = markdown
        result["processing_time"] = time.time() - start
        result["status"] = "completed"
        return result

    async def _execute_primary(self, pdf_path: str, strategy: str, preferred: str) -> OCRResult:
        if preferred and preferred in self.engines:
            engine = self.engines[preferred]
            if await engine.is_available():
                result = await engine.convert(pdf_path)
                if result.success:
                    return result
                logger.warning("Preferred engine %s failed, falling back: %s", preferred, result.error)
            else:
                logger.warning("Preferred engine %s is not available, falling back", preferred)

        priority = ["dolphin", "docling", "mineru", "marker", "surya", "paddleocr", "nougat"]
        if strategy == "marker_only":
            priority = ["marker", "mineru", "docling"]
        elif strategy == "docling_only":
            priority = ["docling", "marker", "mineru"]

        for name in priority:
            if name in self.engines:
                engine = self.engines[name]
                if await engine.is_available():
                    result = await engine.convert(pdf_path)
                    if result.success:
                        return result
        return OCRResult(success=False, error="No available engine could process the file")

    async def _correction_pipeline(self, markdown: str) -> tuple[str, list]:
        corrections = []

        if self.llm_router and self.llm_router.list_providers():
            llm = lambda prompt: self.llm_router.route("ocr_correction", [{"role": "user", "content": prompt}])
        else:
            llm = None

        markdown = await self.table_corrector.correct(markdown, llm)
        corrections.append("table_correction")
        markdown = await self.formula_corrector.correct(markdown, llm)
        corrections.append("formula_correction")
        markdown = await self.ordering_corrector.correct(markdown, llm)
        corrections.append("ordering_correction")

        return markdown, corrections

    async def _fallback_correction(self, pdf_path: str, markdown: str, quality: dict) -> Optional[dict]:
        for name in self.engines:
            if await self.engines[name].is_available():
                result = await self.engines[name].convert(pdf_path)
                if result.success:
                    new_quality = await self.scorer.score(result.markdown)
                    if new_quality["total"] > quality["total"]:
                        markdown, corrections = await self._correction_pipeline(result.markdown)
                        return {"markdown": markdown, "corrections": [f"fallback_to_{name}"] + corrections}
        return None
