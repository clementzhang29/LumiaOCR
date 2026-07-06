# OCR Agent 智能文档解析与知识问答系统项目介绍

作者：张春  
整理：AI 根据项目文件整理生成  
更新时间：2026-07-06（Asia/Shanghai）  
GitHub：https://github.com/clementzhang29/ocr-agent-document-rag

## 1. 项目定位

OCR Agent 是一个面向 PDF、扫描件、科研论文和图文表格混排资料的智能文档解析系统。项目将“文档上传、文档体检、OCR 模型路由、版面修复、Markdown/HTML 输出、OCR 后 RAG 问答”整合到同一个 Web 工作台中，目标是让用户把 PDF 直接转化为可阅读、可追问、可导出、可二次整理的知识资产。

它不是一个单模型 OCR Demo，而是一套可扩展的 OCR 智能体框架。系统会先分析文档特征，再选择更合适的 OCR/解析引擎，并在输出后进行纠错、排版和知识库入库。

## 2. 适用场景

- 科研论文 PDF 的图文表格混排解析。
- 扫描 PDF、图片型 PDF、普通文本 PDF 的统一处理。
- 中英文技术资料、论文、报告、说明书的 Markdown 转换。
- OCR 后多文档问答、摘要、翻译、表格提取和素材整理。
- 本地部署的文档解析工作台和简历项目展示。

## 3. 技术栈

| 层级 | 技术/组件 | 说明 |
| --- | --- | --- |
| 前端 | Vue 3、Vite、Naive UI、Pinia、Axios、Ionicons | 构建 OCR 智能体工作台、任务队列、进度窗口、RAG 对话区 |
| 后端 | Python、FastAPI、Uvicorn、Pydantic、asyncio | 提供 OCR 任务 API、Provider API、RAG API 和静态前端服务 |
| 文档分析 | PyMuPDF/fitz | 分析页数、文本层、扫描状态、图片、表格、公式和语言线索 |
| OCR/解析引擎 | Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat | 根据文档类型路由到不同引擎 |
| 纠错与清洗 | 表格纠错、公式纠错、阅读顺序纠错、Markdown 清洗、质量评分 | 提升 OCR 输出稳定性 |
| RAG | 内存文档库、文本切块、关键词重叠检索、LLM 可选增强 | 支持 OCR 后文档问答 |
| LLM 接入 | OpenAI-compatible Provider、Anthropic Provider | 用于纠错增强、总结、翻译和问答 |
| 导出 | Markdown 下载、布局感知 HTML 导出 | 保留正文、页面图、图片、表格截图和学术风格排版 |

## 4. 六层 OCR 智能体架构

1. 输入接入层  
   接收多 PDF 上传，创建任务 ID，维护任务队列、文件路径、上传状态和前端显示状态。

2. 文档体检层  
   使用 PDFAnalyzer 分析页数、文本层、是否扫描件、图片/表格/公式线索、语言与文档类型，为后续路由提供依据。

3. 模型路由层  
   根据文档体检结果选择合适的 OCR/解析引擎。复杂科研论文优先进入 Dolphin-v2，普通 PDF 可进入 Marker、Docling、MinerU，扫描件可进入 Surya 或 PaddleOCR。

4. OCR 解析层  
   调用具体引擎生成 Markdown 或结构化输出，并记录处理事件、错误、耗时和中间结果。

5. 纠错排版层  
   对表格、公式、阅读顺序和 Markdown 进行修复；通过质量评分判断是否需要 fallback 到其他引擎或进行补救清洗。

6. 知识交互层  
   将 OCR 结果自动写入轻量 RAG 知识库，支持多文档问答、摘要、翻译、提取表格、素材整理和文件导出。

## 5. 核心功能

### 5.1 多文档 OCR

用户可一次上传多个 PDF。系统会为每个文件创建独立任务，前端显示任务队列、当前状态、估算进度和过程日志。完成后可以查看 OCR Markdown 结果并下载。

### 5.2 自动模型选择

用户不需要完全理解每个 OCR 模型的差异。系统会先做文档体检，再根据文档类型选择引擎。例如科研论文、图文表格混排、多栏正文和公式较多的文档，会优先走 Dolphin-v2 或学术文档增强路线。

### 5.3 OCR 后 RAG 问答

OCR 完成后，Markdown 内容自动进入知识库。用户可以在聊天区针对 OCR 后的文档提问，例如：

- 总结这篇论文的研究目标和方法。
- 翻译为中文。
- 提取所有表格并解释含义。
- 整理图片素材和对应说明。
- 生成学术报告大纲。

### 5.4 智能进度与过程窗口

系统将“文件上传进度”和“OCR 处理进度”分离。上传完成后，前端继续显示 OCR 阶段的智能估算进度、关键过程消息和当前处理阶段，避免用户误以为程序卡住。

### 5.5 版面感知 HTML 导出

项目提供 `scripts/export_html.py`，可把 PDF 和 OCR Markdown 重新组织成学术风格 HTML。导出结果尽量保留正文排版、页面图、图片区域和表格截图，适合展示、阅读和复盘 OCR 效果。

## 6. 模型支持

| 引擎 | 作用定位 | 适合场景 |
| --- | --- | --- |
| Dolphin-v2 | 复杂科研论文与版面解析增强 | 多栏论文、图文表格混排、公式和复杂页面 |
| MinerU | 学术 PDF 和结构化解析 | 论文、报告、扫描文档 |
| Marker | PDF 转 Markdown | 结构相对清晰的 PDF |
| Docling | 通用文档结构解析 | 通用 PDF、段落与表格结构 |
| Surya | OCR 与版面检测 | 扫描件、多语言 OCR |
| PaddleOCR | 通用 OCR 基线 | 中文、英文图片文字识别 |
| Nougat | 学术论文文本化 | 论文正文、公式和 LaTeX 风格内容 |

## 7. 目录结构

```text
ocr-harness-v0.1.0/
├─ config/                 # OCR/解析引擎配置
├─ docs/                   # 项目介绍、交接、踩坑、简历材料
├─ frontend/               # Vue 3 Web UI
├─ scripts/                # Dolphin 安装与 HTML 导出脚本
├─ src/
│  ├─ correctors/          # 表格、公式、阅读顺序纠错
│  ├─ engines/             # OCR 引擎适配器
│  ├─ formatter/           # Markdown 清洗
│  ├─ llm/                 # LLM Provider 路由
│  ├─ orchestrator/        # 文档分析与 OCR Pipeline
│  ├─ qa/                  # 质量评分
│  └─ web/                 # FastAPI 服务
├─ tests/                  # 测试脚本与样例 PDF
├─ README.md
└─ run_demo.bat
```

## 8. 项目价值

本项目的关键价值在于把 OCR 从“单次识别工具”升级为“文档智能体”。它不仅识别文字，还关心文档类型、版面结构、模型选择、输出质量、用户等待体验和 OCR 后知识利用。对个人项目展示、科研资料整理和智能文档处理产品原型都有较高参考价值。
