"""端到端测试 — 直接调用 Pipeline（不依赖 HTTP 服务器）。

预期输出：
  Engine: <name>
  Quality: <0-1>
  MD chars: <n>
  MD chars > 0  ->  PASS
"""
import os
import sys
import asyncio
import time
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.engines import SuryaEngine, DoclingEngine, MinerUEngine
from src.qa import QualityScorer
from src.formatter import MarkdownCleaner


async def main() -> int:
    pdf = ROOT / "tests" / "test_sample.pdf"
    if not pdf.exists():
        print(f"[fatal] missing {pdf}")
        return 2

    # 1) OCR
    # Try surya first; if it fails (model not downloaded), fall back to docling
    t0 = time.time()
    engine_names = [
        ("Surya", SuryaEngine({"gpu": True})),
        ("Docling", DoclingEngine({"gpu": True})),
        ("MinerU", MinerUEngine({"gpu": True})),
    ]

    result = None
    engine_used = ""
    for name, eng in engine_names:
        if not await eng.is_available():
            continue
        result = await eng.convert(str(pdf))
        if result.success and len(result.markdown) > 0:
            engine_used = name
            break
        print(f"  [{name}] skipped (success={result.success}, len={len(result.markdown)})")

    if result is None or not result.success:
        print("[fatal] no engine could convert the file")
        return 3

    md = result.markdown
    elapsed = time.time() - t0

    # 2) Quality
    scorer = QualityScorer()
    quality = await scorer.score(md)

    # 3) Format
    cleaner = MarkdownCleaner()
    md = cleaner.clean(md)

    # Output
    print(f"Engine:  {engine_used}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Quality: {quality['total']}")
    print(f"MD chars:{len(md)}")
    if md:
        print(f"Preview: {md[:200]}")
    print()
    if len(md) > 0:
        print("[PASS]")
        return 0
    print("[FAIL]")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
