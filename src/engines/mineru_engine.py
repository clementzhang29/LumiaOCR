"""MinerU 引擎封装 — magic-pdf 1.x 兼容。

要点:
  - 默认设置 `os.environ["CUDA_VISIBLE_DEVICES"] = ""`，避免 torch 在 Windows
    上加载 CUDA DLL 失败的问题。
  - 调用 `do_parse` 真正执行解析；如果模型权重缺失，会被 magic-pdf 自动下载
    (默认到 `~/magic-pdf`)，失败时降级为空 Markdown 并返回错误。
"""
from .base import BaseEngine, OCRResult
import os
import time
import shutil
import tempfile
from pathlib import Path


def _ensure_cpu_env() -> None:
    """在 Windows 上强制 CPU，避免 torch 的 CUDA DLL 加载错误。"""
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


def _ensure_config_env() -> None:
    if os.environ.get("MINERU_TOOLS_CONFIG_JSON"):
        return
    config_path = Path(__file__).resolve().parents[2] / "config" / "magic-pdf.json"
    os.environ["MINERU_TOOLS_CONFIG_JSON"] = str(config_path)


class MinerUEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "MinerU"

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        _ensure_cpu_env()
        _ensure_config_env()
        try:
            from magic_pdf.tools.common import do_parse
            from magic_pdf.config.enums import SupportedPdfParseMethod
            from magic_pdf.config.make_content_config import MakeMode
            from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
            from magic_pdf.data.dataset import PymuDocDataset
            import fitz
        except ImportError as exc:
            return OCRResult(
                success=False,
                error=f"MinerU not installed ({exc}). Run: pip install magic-pdf",
                engine=self.name,
            )

        try:
            output_dir = Path(tempfile.mkdtemp(prefix="mineru_"))
            pdf_stem = Path(pdf_path).stem
            ds = PymuDocDataset(fitz.open(pdf_path).tobytes(), lang=kwargs.get("lang", None))

            do_parse(
                output_dir=str(output_dir),
                pdf_file_name=pdf_stem,
                pdf_bytes_or_dataset=ds,
                model_list=[],
                parse_method=SupportedPdfParseMethod.OCR.value,
                debug_able=False,
                f_draw_span_bbox=False,
                f_draw_layout_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_json=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
                f_make_md_mode=MakeMode.MM_MD,
                lang=kwargs.get("lang", None),
            )

            local_md_dir = output_dir / pdf_stem / SupportedPdfParseMethod.OCR.value
            md_path = local_md_dir / f"{pdf_stem}.md"
            markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

            try:
                shutil.rmtree(output_dir, ignore_errors=True)
            except Exception:
                pass

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
            import magic_pdf  # noqa: F401
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {
            "name": "MinerU",
            "gpu": self.config.get("gpu", True),
            "lang": "multi",
        }
