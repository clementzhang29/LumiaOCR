# LumiaOCR v1.0 项目介绍

作者：张春  
整理：AI 根据项目文件整理生成  
版本：v1.0  
发布时间：2026-07-07（Asia/Shanghai）  
GitHub：https://github.com/clementzhang29/LumiaOCR

## 1. 项目定位

LumiaOCR 是一个面向 PDF、扫描件、科研论文和图文表格混排资料的智能文档解析系统。项目将“文档上传、文档体检、OCR 模型路由、版面修复、Markdown/HTML 输出、OCR 后 RAG 问答”整合到同一个本地化 Web 工作台中，目标是让用户把 PDF 直接转化为可阅读、可追问、可导出、可二次整理的知识资产。

LumiaOCR v1.0 的核心定位是：本地运行、过程透明、多模型路由、科研论文增强、OCR 后可问答。

## 2. 适用场景

- 科研论文 PDF 的图文表格混排解析。
- 扫描 PDF、图片型 PDF、普通文本 PDF 的统一处理。
- 中英文技术资料、论文、报告、说明书的 Markdown 转换。
- OCR 后多文档问答、摘要、翻译、表格提取和素材整理。
- 本地部署的智能文档处理工作台和简历项目展示。

## 3. 技术栈

| 层级 | 技术/组件 | 说明 |
| --- | --- | --- |
| 前端 | Vue 3、Vite、Naive UI、Pinia、Axios、Ionicons | 构建 LumiaOCR 工作台、任务队列、进度窗口、RAG 对话区 |
| 后端 | Python、FastAPI、Uvicorn、Pydantic、asyncio | 提供 OCR 任务 API、Provider API、RAG API 和静态前端服务 |
| 文档分析 | PyMuPDF/fitz | 分析页数、文本层、扫描状态、图片、表格、公式和语言线索 |
| OCR/解析引擎 | Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat | 根据文档类型路由到不同引擎 |
| 纠错与清洗 | 表格纠错、公式纠错、阅读顺序纠错、Markdown 清洗、质量评分 | 提升 OCR 输出稳定性 |
| RAG | 内存文档库、文本切块、关键词重叠检索、LLM 可选增强 | 支持 OCR 后文档问答 |
| LLM 接入 | OpenAI-compatible Provider、Anthropic Provider | 用于纠错增强、总结、翻译和问答 |
| 导出 | Markdown 下载、布局感知 HTML 导出 | 保留正文、页面图、图片、表格截图和学术风格排版 |

## 4. 六层 OCR 智能体架构

1. 输入接入层：接收多 PDF 上传，创建任务 ID，维护任务队列、文件路径、上传状态和前端显示状态。
2. 文档体检层：分析页数、文本层、是否扫描件、图片/表格/公式线索、语言与文档类型。
3. 模型路由层：复杂科研论文优先 Dolphin-v2，普通 PDF 可进入 Marker、Docling、MinerU，扫描件可进入 Surya 或 PaddleOCR。
4. OCR 解析层：调用具体引擎生成 Markdown 或结构化输出，并记录处理事件、错误、耗时和中间结果。
5. 纠错排版层：对表格、公式、阅读顺序和 Markdown 进行修复，通过质量评分判断是否 fallback。
6. 知识交互层：将 OCR 结果自动写入轻量 RAG 知识库，支持多文档问答、摘要、翻译、提取表格、素材整理和文件导出。

## 5. v1.0 定版功能

- 多文档 OCR 上传与队列管理。
- 智能预估进度和实时过程消息。
- 自动模型路由与复杂科研论文增强。
- OCR Markdown 自动入库。
- OCR 后多文档 RAG 问答。
- 常用操作标签：总结、翻译、表格提取、图片素材整理、学术结构重排、素材整合。
- OpenAI-compatible API Provider 配置。
- Markdown 与布局感知 HTML 输出。
- 本地化浏览器运行，支持 Windows 桌面环境快速启动。

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
LumiaOCR/
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

LumiaOCR 的关键价值在于把 OCR 从“单次识别工具”升级为“文档智能体”。它不仅识别文字，还关心文档类型、版面结构、模型选择、输出质量、用户等待体验和 OCR 后知识利用。对科研资料整理、智能文档处理产品原型、个人项目展示和简历作品集都有较高参考价值。
