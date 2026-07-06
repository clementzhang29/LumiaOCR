# AI 交接文档

作者：张春  
整理：AI 根据项目文件整理生成  
更新时间：2026-07-07（Asia/Shanghai）
版本：v1.0  
项目仓库：https://github.com/clementzhang29/LumiaOCR

## 1. 项目当前状态

项目已经形成可运行的 LumiaOCR Web 工作台，主要能力包括：

- FastAPI 后端服务。
- Vue 3 + Naive UI 前端。
- 多 PDF 上传和 OCR 任务管理。
- 文档自动体检与 OCR 模型路由。
- Dolphin-v2 科研论文增强解析接入。
- OCR 结果 Markdown 输出与下载。
- OCR 后文档自动进入轻量 RAG 知识库。
- 支持对 OCR 后多文档进行聊天问答、摘要、翻译、表格提取和素材整理。
- 支持 OpenAI-compatible Provider 配置。
- 支持布局感知 HTML 导出脚本。
- 项目介绍 HTML、截图和说明文档已纳入 `docs/`。

## 2. 关键路径

| 路径 | 说明 |
| --- | --- |
| `src/web/app.py` | FastAPI 主应用，包含 OCR API、Provider API、RAG API、任务状态和静态前端服务 |
| `src/web/main.py` | 后端启动入口 |
| `src/orchestrator/analyzer.py` | PDF 文档体检，判断页数、文本层、扫描件、图片、表格、公式、语言和推荐引擎 |
| `src/orchestrator/pipeline.py` | OCRPipeline 主流程，负责引擎选择、调用、纠错、评分和输出 |
| `src/engines/` | 各 OCR/解析引擎适配器 |
| `src/engines/dolphin_engine.py` | Dolphin-v2 接入逻辑 |
| `src/correctors/` | 表格、公式、阅读顺序纠错模块 |
| `src/formatter/markdown_cleaner.py` | Markdown 输出清洗 |
| `src/llm/` | LLM Provider 抽象、路由和兼容接口 |
| `frontend/src/views/Rag.vue` | OCR 智能体/RAG 工作台主界面 |
| `frontend/src/views/Providers.vue` | API Provider 设置页 |
| `scripts/export_html.py` | PDF + Markdown 布局感知 HTML 导出 |
| `docs/` | 项目文档、介绍页和截图 |

## 3. 后端设计要点

### 3.1 OCR 任务

后端维护内存任务表。用户上传 PDF 后，系统保存文件、创建任务 ID，并异步执行 OCR Pipeline。前端通过状态接口轮询任务进度。

由于 OCR 是长耗时任务，项目中已经将重处理流程放入后台线程执行，避免 FastAPI 事件循环被阻塞，解决了“上传完成但页面一直没反馈”的问题。

### 3.2 文档分析与模型路由

`PDFAnalyzer` 会检查：

- 页数。
- 是否有文本层。
- 是否扫描件。
- 图片数量。
- 表格线索。
- 公式线索。
- 语言线索。
- 文档类型。
- 推荐引擎。

路由策略的核心思想是：先理解文档，再选择模型。复杂科研论文优先 Dolphin-v2；普通 PDF、扫描件和通用资料按场景选择 Marker、Docling、MinerU、Surya、PaddleOCR 或 Nougat。

### 3.3 OCR 后 RAG

OCR Markdown 完成后会被切块并加入内存知识库。检索采用轻量 token overlap 思路，配置 LLM 后可以生成更自然的回答；没有 LLM 时仍可返回基于片段的抽取式答案。

## 4. 前端设计要点

前端主界面围绕“用户不要傻等”设计：

- 上传区支持多 PDF。
- 任务队列显示每个文件状态。
- 智能预估进度区显示 OCR 阶段，而不是只显示浏览器上传进度。
- 过程消息窗口动态显示关键事件。
- 文档知识库区展示 OCR 后可问答的文档。
- 对话区支持自由提问。
- 引导标签提供常用操作：翻译为中文、总结、提取表格、素材整合、学术提纲、导出。

## 5. 模型与大文件说明

GitHub 仓库不包含以下内容：

- Dolphin-v2 权重。
- 第三方 Dolphin 源码压缩包。
- `frontend/node_modules`。
- 用户上传 PDF。
- OCR 导出结果。
- 运行日志。

这些内容通过 `.gitignore` 排除。新环境需要按安装文档重新准备依赖和模型。

## 6. 当前限制

- 任务状态和 RAG 知识库目前主要在内存中，服务重启后会丢失。
- Provider Key 当前主要保存在进程内存中，不是持久化密钥管理。
- OCR 引擎在不同机器上的可用性取决于本地依赖、模型权重、CUDA 和硬件资源。
- HTML 导出已增强图片和表格展示，但要达到完全原版 PDF 级坐标还原，还需要更细的版面块坐标和阅读顺序模型。

## 7. 后续接手建议

1. 先运行基础 Web 服务，确认前端页面可打开。
2. 用小 PDF 测通上传、OCR 任务、状态轮询和结果下载。
3. 配置 Provider，测试 OCR 后 RAG 问答。
4. 再接入 Dolphin-v2 或其他重模型，逐步验证复杂论文。
5. 如要产品化，优先加入持久化数据库、任务队列、WebSocket 事件流和向量数据库。

## 8. 推荐下一阶段改造

- 使用 SQLite/PostgreSQL 持久化任务、文档、Provider 配置和聊天记录。
- 使用 Redis/RQ/Celery 处理 OCR 队列。
- 使用 WebSocket 或 Server-Sent Events 替代轮询。
- 接入 Chroma、Milvus、Qdrant 或 FAISS 做向量检索。
- 给每个 OCR 引擎增加可用性检测和健康状态。
- 引入 OCR 质量评测集，对不同文档类型记录模型效果。
- 给 HTML 导出增加更精确的版面坐标映射。


