"""Dolphin-v2 engine wrapper for complex scientific-paper parsing.

Dolphin is integrated as an optional external engine because the model is
large and its upstream repo owns the inference code. Configure with:

  DOLPHIN_REPO_DIR  -> path to ByteDance/Dolphin repository
  DOLPHIN_MODEL_DIR -> path to ByteDance/Dolphin-v2 Hugging Face model
"""
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from .base import BaseEngine, OCRResult


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_DIR = ROOT / "third_party" / "Dolphin-master"
DEFAULT_MODEL_DIR = ROOT / "models" / "dolphin-v2"


class DolphinEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "Dolphin-v2"

    @property
    def repo_dir(self) -> Path:
        return Path(os.environ.get("DOLPHIN_REPO_DIR", self.config.get("repo_dir", DEFAULT_REPO_DIR)))

    @property
    def model_dir(self) -> Path:
        return Path(os.environ.get("DOLPHIN_MODEL_DIR", self.config.get("model_dir", DEFAULT_MODEL_DIR)))

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        if not await self.is_available():
            return OCRResult(
                success=False,
                error="Dolphin-v2 is not available. Run scripts/install_dolphin.ps1 and install qwen-vl-utils.",
                engine=self.name,
            )

        output_dir = Path(tempfile.mkdtemp(prefix="dolphin_"))
        timeout = int(self.config.get("timeout", 1800))
        max_batch_size = str(kwargs.get("max_batch_size", self.config.get("max_batch_size", 2)))

        cmd = [
            sys.executable,
            "demo_page.py",
            "--model_path",
            str(self.model_dir),
            "--save_dir",
            str(output_dir),
            "--input_path",
            str(Path(pdf_path).resolve()),
            "--max_batch_size",
            max_batch_size,
            "--post_process",
        ]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.repo_dir) + os.pathsep + env.get("PYTHONPATH", "")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo_dir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                return OCRResult(
                    success=False,
                    error=f"Dolphin failed with code {proc.returncode}: {stderr_text or stdout_text}",
                    engine=self.name,
                    processing_time=time.time() - start,
                )

            stem = Path(pdf_path).stem
            md_path = output_dir / "markdown" / f"{stem}.md"
            json_path = output_dir / "recognition_json" / f"{stem}.json"
            markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
            json_data = None
            if json_path.exists():
                json_data = json.loads(json_path.read_text(encoding="utf-8"))

            return OCRResult(
                markdown=markdown,
                json_data=json_data,
                metadata={
                    "repo_dir": str(self.repo_dir),
                    "model_dir": str(self.model_dir),
                    "stdout_tail": stdout_text[-2000:],
                },
                engine=self.name,
                processing_time=time.time() - start,
            )
        except asyncio.TimeoutError:
            return OCRResult(
                success=False,
                error=f"Dolphin timed out after {timeout}s",
                engine=self.name,
                processing_time=time.time() - start,
            )
        except Exception as exc:
            return OCRResult(success=False, error=str(exc), engine=self.name, processing_time=time.time() - start)

    async def is_available(self) -> bool:
        if not (self.repo_dir / "demo_page.py").exists():
            return False
        required_files = [
            self.model_dir / "config.json",
            self.model_dir / "model.safetensors.index.json",
            self.model_dir / "model-00001-of-00002.safetensors",
            self.model_dir / "model-00002-of-00002.safetensors",
        ]
        if not all(path.exists() for path in required_files):
            return False
        try:
            import qwen_vl_utils  # noqa: F401
            from transformers import Qwen2_5_VLForConditionalGeneration  # noqa: F401
            return True
        except Exception:
            return False

    def get_metadata(self) -> dict:
        return {
            "name": "Dolphin-v2",
            "gpu": self.config.get("gpu", True),
            "lang": "multi",
            "specialty": "complex_scientific_paper_layout",
            "repo_dir": str(self.repo_dir),
            "model_dir": str(self.model_dir),
        }
