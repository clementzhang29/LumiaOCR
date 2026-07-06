"""端到端 API 测试：注册 Provider + 上传 PDF + 轮询结果。"""
import asyncio
import httpx
import sys

HOST = "http://127.0.0.1:8080"


async def main():
    async with httpx.AsyncClient(base_url=HOST, timeout=120.0) as client:
        # 1. Health
        r = await client.get("/api/health")
        print("Health:", r.json())

        # 2. Register LLM Provider
        payload = {
            "name": "my-openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-fake-key-for-pipeline",
            "model": "gpt-4o-mini",
        }
        r = await client.post("/api/providers", json=payload)
        print("Register:", r.status_code, r.json())

        # 3. List providers
        r = await client.get("/api/providers")
        print("Providers:", r.json())

        # 4. List engines
        r = await client.get("/api/engines")
        engines = r.json()
        avail = [e["name"] for e in engines["engines"] if e.get("available")]
        print("Available engines:", avail)

        # 5. Upload PDF
        with open("tests/test_sample.pdf", "rb") as f:
            files = {"file": ("test_sample.pdf", f, "application/pdf")}
            r = await client.post(
                "/api/convert",
                files=files,
                data={"strategy": "auto", "preferred_engine": ""},
            )
        print("Convert:", r.status_code, r.json())
        task_id = r.json()["task_id"]

        # 6. Poll result
        for i in range(180):
            r = await client.get(f"/api/status/{task_id}")
            info = r.json()
            status = info.get("status")
            if status == "completed":
                res = await client.get(f"/api/result/{task_id}")
                result = res.json()
                engine = result.get("engine_used", "?")
                quality = result.get("quality_score", 0)
                md = result.get("markdown", "")
                print()
                print(f"=== OCR-Harness E2E Result ===")
                print(f"Status:  completed")
                print(f"Engine:  {engine}")
                print(f"Quality: {quality}")
                print(f"MD chars:{len(md)}")
                if md:
                    preview = md.replace("\n", " ")[:300]
                    print(f"Preview: {preview}...")
                if len(md) > 0:
                    print("[PASS] MD chars > 0")
                    return 0
                else:
                    print("[FAIL] MD is empty")
                    return 1
            elif status == "failed":
                print(f"Failed: {info.get('error', '?')}")
                return 2
            if i % 15 == 0:
                print(f"  polling #{i}: status={status} progress={info.get('progress')}")
            await asyncio.sleep(1)

        print("[FAIL] Timeout")
        return 3


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
