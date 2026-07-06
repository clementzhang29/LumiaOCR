"""
OCR-Harness FastAPI Web 应用 — 主入口文件。
提供 REST API:
  - POST /api/convert     上传 PDF 并执行 OCR
  - GET  /api/status/{id}  查询任务状态
  - GET  /api/result/{id}  获取转换结果
  - POST /api/providers    注册 LLM API Provider
  - GET  /api/providers    列出已注册 Provider
  - POST /api/providers/verify  验证所有 Provider 连接
"""
import os
import uuid
import json
import asyncio
import logging
import math
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..llm import LLMRouter, APIKeyManager, APIKeyEntry
from ..engines import (
    MinerUEngine, MarkerEngine, DoclingEngine,
    PaddleOCREngine, NougatEngine, SuryaEngine, DolphinEngine
)
from ..orchestrator import DocumentAnalyzer, OCRPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="OCR-Harness", version="0.1.0")
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS)), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
UPLOAD_DIR = Path(os.environ.get("OCR_HARNESS_UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

tasks: dict[str, dict] = {}
rag_docs: dict[str, dict] = {}
rag_chunks: list[dict] = []
llm_router = LLMRouter()
api_key_manager = APIKeyManager()
analyzer = DocumentAnalyzer()

# 引擎注册
ENGINE_CONFIG = {
    "mineru": {"gpu": True, "timeout": 300},
    "marker": {"gpu": True, "timeout": 300},
    "docling": {"gpu": True, "timeout": 300},
    "surya": {"gpu": True, "timeout": 300},
    "paddleocr": {"gpu": True, "lang": "ch", "timeout": 300},
    "nougat": {"gpu": True, "timeout": 600},
    "dolphin": {"gpu": True, "timeout": 1800, "max_batch_size": 2},
}

_engines = {}


def _task_event(task_id: str, stage: str, message: str, progress: int | None = None):
    task = tasks.get(task_id)
    if not task:
        return
    event = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "message": message,
    }
    task.setdefault("events", []).append(event)
    task["stage_message"] = message
    task["updated_at"] = event["time"]
    if progress is not None:
        task["progress"] = progress

def get_engines():
    if not _engines:
        engines = {
            "mineru": MinerUEngine(ENGINE_CONFIG["mineru"]),
            "marker": MarkerEngine(ENGINE_CONFIG["marker"]),
            "docling": DoclingEngine(ENGINE_CONFIG["docling"]),
            "dolphin": DolphinEngine(ENGINE_CONFIG["dolphin"]),
            "surya": SuryaEngine(ENGINE_CONFIG["surya"]),
            "paddleocr": PaddleOCREngine(ENGINE_CONFIG["paddleocr"]),
            "nougat": NougatEngine(ENGINE_CONFIG["nougat"]),
        }
        _engines.update(engines)
    return _engines


def _run_pipeline_sync(pdf_path: str, strategy: str, routed_engine: str) -> dict:
    """Run heavy OCR work in a worker thread so the FastAPI event loop stays responsive."""
    pipeline = OCRPipeline(get_engines(), llm_router if llm_router.list_providers() else None)
    return asyncio.run(pipeline.run(pdf_path, strategy, routed_engine))

# === API Models ===

class ProviderRegister(BaseModel):
    name: str
    base_url: str
    api_key: str
    model: str = ""

class ConvertRequest(BaseModel):
    strategy: str = "auto"
    preferred_engine: str = ""

class RAGQuery(BaseModel):
    question: str
    top_k: int = 5

class AgentAction(BaseModel):
    action: str
    doc_ids: list[str] | None = None
    question: str = ""
    top_k: int = 6

# === API Routes ===

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/engines")
async def list_engines():
    engines = get_engines()
    result = []
    for name, engine in engines.items():
        info = engine.get_metadata()
        display_name = info.pop("name", name)
        info["available"] = await engine.is_available()
        result.append({"id": name, "name": display_name, **info})
    return {"engines": result}

@app.post("/api/providers")
async def register_provider(data: ProviderRegister):
    """注册 LLM API Provider"""
    entry = APIKeyEntry(
        name=data.name,
        provider="",
        base_url=data.base_url,
        model=data.model,
        api_key=data.api_key,
    )
    api_key_manager.add_key(entry)
    provider = llm_router.register(data.name, data.base_url, data.api_key, data.model)
    return {"status": "registered", "name": data.name, "provider": provider.config.provider}

@app.get("/api/providers")
async def list_providers():
    return {"providers": llm_router.list_providers(), "keys": api_key_manager.list_keys()}

@app.post("/api/providers/delete/{name}")
async def delete_provider(name: str):
    llm_router.remove(name)
    api_key_manager.remove_key(name)
    return {"status": "deleted", "name": name}

@app.post("/api/providers/verify")
async def verify_providers():
    results = await llm_router.verify_all()
    return {"results": results}

@app.get("/api/rag/status")
async def rag_status():
    return {
        "documents": list(rag_docs.values()),
        "chunk_count": len(rag_chunks),
        "llm_enabled": bool(llm_router.list_providers()),
    }

@app.get("/api/agent/documents")
async def agent_documents():
    return {
        "documents": list(rag_docs.values()),
        "chunk_count": len(rag_chunks),
        "tasks": list(tasks.values()),
        "llm_enabled": bool(llm_router.list_providers()),
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }

@app.post("/api/agent/upload")
async def agent_upload(
    files: list[UploadFile] = File(...),
    strategy: str = Form("auto"),
    preferred_engine: str = Form(""),
):
    if not files:
        raise HTTPException(400, "No files uploaded")
    created = []
    for file in files:
        task_id = str(uuid.uuid4())
        ext = Path(file.filename or "document.pdf").suffix or ".pdf"
        save_path = UPLOAD_DIR / f"{task_id}{ext}"
        content = await file.read()
        save_path.write_bytes(content)
        tasks[task_id] = {
            "id": task_id,
            "filename": file.filename,
            "status": "queued",
            "progress": 0,
            "stage_message": "任务已进入队列，完成 OCR 后会自动进入问答知识库",
            "events": [{
                "time": datetime.now().isoformat(timespec="seconds"),
                "stage": "queued",
                "message": "已接收文档，等待 OCR 智能体调度",
            }],
            "created_at": datetime.now().isoformat(),
        }
        asyncio.create_task(_run_conversion(task_id, str(save_path), strategy, preferred_engine))
        created.append({"task_id": task_id, "filename": file.filename, "status": "queued"})
    return {"tasks": created}

@app.post("/api/agent/action")
async def agent_action(data: AgentAction):
    action_map = {
        "translate_zh": "请把 OCR 后的核心内容翻译成流畅中文，保留标题、术语、数字、表格含义和引用线索。",
        "summary": "请总结这些 OCR 文档的主题、核心结论、关键证据和可复用素材。",
        "tables": "请提取并整理文档中的表格信息；如果表格识别不完整，请指出缺失和可能原因。",
        "figures": "请整理文档中的图片、图表、公式、实验素材和它们对应的正文语境。",
        "outline": "请按学术文献标准重组文档结构：标题、摘要、方法、实验、结论、局限、引用线索。",
        "materials": "请把 OCR 内容整理成可用于 RAG/知识库/汇报的素材包，按主题分组并列出待核对项。",
    }
    question = data.question.strip() or action_map.get(data.action, data.action)
    if not question:
        raise HTTPException(400, "Action or question is required")
    if not rag_chunks:
        raise HTTPException(400, "Knowledge base is empty")
    matches = _retrieve_chunks(question, max(1, min(data.top_k, 10)), data.doc_ids or None)
    context = "\n\n".join(
        f"[{idx + 1}] {item['filename']} chunk {item['index'] + 1}\n{item['text']}"
        for idx, item in enumerate(matches)
    )
    answer = ""
    used_llm = False
    if llm_router.list_providers():
        prompt = (
            "你是 OCR 文档智能体。只能依据给定 OCR 文档片段回答。"
            "回答要结构清晰，必要时指出 OCR 识别不确定处，并用 [1] 这样的编号标注依据。\n\n"
            f"任务：{question}\n\nOCR 文档片段：\n{context}"
        )
        try:
            answer = await llm_router.route("ocr_correction", [{"role": "user", "content": prompt}])
            used_llm = True
        except Exception as exc:
            logger.warning("Agent action LLM failed, using extractive fallback: %s", exc)
    if not answer:
        answer = _extractive_answer(question, matches)
    return {
        "answer": answer,
        "citations": [
            {
                "rank": idx + 1,
                "filename": item["filename"],
                "doc_id": item["doc_id"],
                "chunk_id": item["chunk_id"],
                "score": round(item["score"], 4),
                "text": item["text"],
            }
            for idx, item in enumerate(matches)
        ],
        "used_llm": used_llm,
    }

@app.post("/api/rag/ingest")
async def rag_ingest(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "document"
    suffix = Path(filename).suffix.lower()
    text = _extract_rag_text(content, suffix)
    if not text.strip():
        raise HTTPException(400, "No readable text extracted from file")

    doc = _ingest_rag_text(text, filename, source="upload")
    return {"document": doc, "chunk_count": len(rag_chunks)}

@app.post("/api/rag/query")
async def rag_query(data: RAGQuery):
    question = data.question.strip()
    if not question:
        raise HTTPException(400, "Question is required")
    if not rag_chunks:
        raise HTTPException(400, "Knowledge base is empty")

    matches = _retrieve_chunks(question, max(1, min(data.top_k, 10)))
    context = "\n\n".join(
        f"[{idx + 1}] {item['filename']} chunk {item['index'] + 1}\n{item['text']}"
        for idx, item in enumerate(matches)
    )
    answer = ""
    used_llm = False
    if llm_router.list_providers():
        prompt = (
            "Answer the question using only the provided context. "
            "If the context is insufficient, say so. Include citation numbers like [1].\n\n"
            f"Context:\n{context}\n\nQuestion: {question}"
        )
        try:
            answer = await llm_router.route("ocr_correction", [{"role": "user", "content": prompt}])
            used_llm = True
        except Exception as exc:
            logger.warning("RAG LLM answer failed, using extractive fallback: %s", exc)

    if not answer:
        answer = _extractive_answer(question, matches)

    return {
        "answer": answer,
        "citations": [
            {
                "rank": idx + 1,
                "filename": item["filename"],
                "chunk_id": item["chunk_id"],
                "score": round(item["score"], 4),
                "text": item["text"],
            }
            for idx, item in enumerate(matches)
        ],
        "used_llm": used_llm,
    }

@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),
    preferred_engine: str = Form(""),
):
    """上传 PDF 并启动 OCR 转换"""
    task_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix if file.filename else ".pdf"
    save_path = UPLOAD_DIR / f"{task_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    tasks[task_id] = {
        "id": task_id,
        "filename": file.filename,
        "status": "queued",
        "progress": 0,
        "stage_message": "任务已进入队列",
        "events": [
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "stage": "queued",
                "message": "已接收 PDF，等待调度",
            }
        ],
        "created_at": datetime.now().isoformat(),
    }

    asyncio.create_task(_run_conversion(task_id, str(save_path), strategy, preferred_engine))
    return {"task_id": task_id, "status": "queued"}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task["status"] != "completed":
        raise HTTPException(400, f"Task not completed, current status: {task['status']}")
    return task

@app.get("/api/download/{task_id}")
async def download_result(task_id: str):
    task = tasks.get(task_id)
    if not task or task["status"] != "completed":
        raise HTTPException(404, "Result not available")
    result_path = UPLOAD_DIR / f"{task_id}_result.md"
    result_path.write_text(task.get("markdown", ""), encoding="utf-8")
    return FileResponse(str(result_path), filename=f"{Path(task['filename']).stem}.md", media_type="text/markdown")

async def _run_conversion(task_id: str, pdf_path: str, strategy: str, preferred_engine: str):
    try:
        tasks[task_id]["status"] = "analyzing"
        _task_event(task_id, "analyzing", "正在读取 PDF 结构、文本层、图片和页面特征", 10)
        analysis = await analyzer.analyze(pdf_path)
        tasks[task_id]["analysis"] = analysis
        _task_event(
            task_id,
            "analyzing",
            f"分析完成：{analysis.get('page_count', 0)} 页，类型 {analysis.get('doc_type', 'unknown')}，推荐 {analysis.get('recommended_engine', 'auto')}",
            20,
        )

        tasks[task_id]["status"] = "converting"
        route_hint = preferred_engine or analysis.get("recommended_engine") or "auto"
        _task_event(task_id, "routing", f"已选择处理策略：{strategy}，首选引擎：{route_hint}", 28)
        _task_event(task_id, "converting", "OCR 引擎正在解析页面、识别文字并整理阅读顺序", 45)
        routed_engine = preferred_engine
        if strategy == "auto" and not routed_engine:
            routed_engine = analysis.get("recommended_engine", "")
        result = await asyncio.to_thread(_run_pipeline_sync, pdf_path, strategy, routed_engine)
        tasks[task_id].update(result)
        _task_event(task_id, "scoring", f"质量评分完成：{result.get('quality_score', 0):.2f}，使用引擎 {result.get('engine_used', 'unknown')}", 86)
        if result.get("corrections"):
            _task_event(task_id, "correction", "已完成表格、公式与阅读顺序校正", 92)
        markdown = result.get("markdown", "")
        if markdown.strip():
            doc = _ingest_rag_text(markdown, tasks[task_id].get("filename") or f"{task_id}.md", task_id=task_id, source="ocr")
            tasks[task_id]["rag_doc_id"] = doc["id"]
            _task_event(task_id, "rag", "OCR 结果已自动进入文档问答知识库", 96)
        _task_event(task_id, "completed", "Markdown 已生成，可预览、下载或直接提问", 100)
        tasks[task_id]["status"] = "completed"
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        _task_event(task_id, "failed", f"处理失败：{e}", 0)
        logger.exception(f"Task {task_id} failed")

def _frontend_index() -> HTMLResponse:
    """提供静态前端页面"""
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>OCR-Harness API</h1><p>Frontend not built. Run <code>cd frontend && npm install && npm run build</code></p>")

@app.get("/", response_class=HTMLResponse)
async def index():
    return _frontend_index()

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")
    return _frontend_index()

def run():
    import uvicorn
    host = os.environ.get("OCR_HARNESS_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_HARNESS_PORT", "8080"))
    uvicorn.run("src.web.app:app", host=host, port=port, reload=True)


def _extract_rag_text(content: bytes, suffix: str) -> str:
    if suffix == ".pdf":
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            try:
                return "\n\n".join(page.get_text("text") for page in doc)
            finally:
                doc.close()
        except Exception as exc:
            raise HTTPException(400, f"PDF text extraction failed: {exc}")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("gbk", errors="ignore")


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end].strip())
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def _ingest_rag_text(text: str, filename: str, task_id: str | None = None, source: str = "upload") -> dict:
    doc_id = task_id or str(uuid.uuid4())
    old = rag_docs.get(doc_id)
    if old:
        rag_chunks[:] = [chunk for chunk in rag_chunks if chunk["doc_id"] != doc_id]
    chunks = _chunk_text(text)
    doc = {
        "id": doc_id,
        "task_id": task_id,
        "filename": filename,
        "source": source,
        "chars": len(text),
        "chunks": len(chunks),
        "created_at": old.get("created_at") if old else datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    rag_docs[doc_id] = doc
    for index, chunk in enumerate(chunks):
        rag_chunks.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}:{index}",
            "index": index,
            "text": chunk,
            "tokens": _tokenize(chunk),
            "filename": filename,
        })
    return doc


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[\w\u4e00-\u9fff]{2,}", text.lower()))


def _retrieve_chunks(question: str, top_k: int, doc_ids: list[str] | None = None) -> list[dict]:
    q_tokens = _tokenize(question)
    allowed = set(doc_ids or [])
    scored = []
    for chunk in rag_chunks:
        if allowed and chunk["doc_id"] not in allowed:
            continue
        tokens = chunk["tokens"]
        if not tokens:
            continue
        overlap = len(q_tokens & tokens)
        if overlap == 0:
            score = 0.0
        else:
            score = overlap / math.sqrt(max(len(tokens), 1))
        item = {k: v for k, v in chunk.items() if k != "tokens"}
        item["score"] = score
        scored.append(item)
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _extractive_answer(question: str, matches: list[dict]) -> str:
    lines = ["基于当前知识库，检索到以下相关片段："]
    for idx, item in enumerate(matches, start=1):
        snippet = item["text"][:420].strip()
        lines.append(f"[{idx}] {snippet}")
    lines.append("如需生成更自然的总结回答，请先在 API 设置页配置 LLM Provider。")
    return "\n\n".join(lines)
