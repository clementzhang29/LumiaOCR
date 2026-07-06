import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import asyncio
from src.engines import DoclingEngine

async def main():
    e = DoclingEngine({"gpu": False})
    print("available:", await e.is_available())
    r = await e.convert(os.path.join(os.path.dirname(__file__), "test_sample.pdf"))
    print("success:", r.success)
    print("error:", (r.error or "")[:500])
    print("md_len:", len(r.markdown))

asyncio.run(main())
