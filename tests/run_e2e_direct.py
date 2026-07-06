"""直接测试 OCR Pipeline，绕过 HTTP API。"""
import sys, os, asyncio, time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.engines import DoclingEngine
from src.qa import QualityScorer
from src.formatter import MarkdownCleaner

async def main():
    pdf = os.path.join(os.path.dirname(__file__), "test_sample.pdf")
    
    # Step 1: OCR
    engine = DoclingEngine({"gpu": False})
    t0 = time.time()
    result = await engine.convert(pdf)
    elapsed = time.time() - t0
    print(f"Engine:  {result.engine}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Success: {result.success}")
    
    if not result.success:
        print(f"Error: {result.error}")
        return 1
    
    md = result.markdown
    
    # Step 2: Quality
    scorer = QualityScorer()
    quality = await scorer.score(md)
    print(f"Quality: {quality['total']}")
    
    # Step 3: Format
    cleaner = MarkdownCleaner()
    md = cleaner.clean(md)
    
    print(f"MD chars:{len(md)}")
    if md:
        print(f"Preview: {md[:300]}")
    
    if len(md) > 0:
        print()
        print("[PASS]")
        return 0
    else:
        print("[FAIL]")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
