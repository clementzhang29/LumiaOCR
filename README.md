# LumiaOCR v1.0

作者：张春  
整理：AI 根据项目文件整理生成  
版本：v1.0  
发布日期：2026-07-07（Asia/Shanghai）

## 项目简介

LumiaOCR 是一个面向 PDF、扫描件、科研论文和图文表格混排资料的智能文档解析与 RAG 问答系统。项目基于 FastAPI + Vue 3 构建本地化 Web 工作台，集成 Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat 等多种 OCR/文档解析引擎，支持文档自动体检、模型路由、OCR 解析、输出排版、Markdown/HTML 导出和 OCR 后多文档问答。

GitHub 仓库：

```text
https://github.com/clementzhang29/LumiaOCR
```

## v1.0 定版能力

- 多 PDF 上传与任务队列。
- PDF 文档体检：页数、文本层、扫描状态、图片、表格、公式、语言和文档类型。
- 多 OCR/解析引擎路由：Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat。
- 科研论文图文表格混排增强解析。
- OCR 输出 Markdown 清洗、纠错和质量评分。
- 智能预估进度与实时过程消息窗口。
- OCR 后文档自动进入轻量 RAG 知识库。
- 支持摘要、翻译、表格提取、素材整理和多文档问答。
- 支持 OpenAI-compatible Provider 配置。
- 支持布局感知 HTML 导出。
- 本地化浏览器运行，前端采用 LumiaOCR 研究工作台视觉风格。

## 快速启动

```powershell
git clone https://github.com/clementzhang29/LumiaOCR.git
cd LumiaOCR
python -m src.web.main
```

默认访问：

```text
http://127.0.0.1:8080/
```

如果端口被占用：

```powershell
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8092
```

访问：

```text
http://127.0.0.1:8092/
```

## 前端构建

```powershell
cd frontend
npm install
npm run build
cd ..
```

## 文档清单

| 文档 | 说明 |
| --- | --- |
| `docs/PROJECT_INTRO.md` | LumiaOCR v1.0 完整项目介绍 |
| `docs/INSTALL_USAGE.md` | 安装与使用文档 |
| `docs/AI_HANDOFF.md` | AI 交接文档 |
| `docs/AGENT_BUILD_PROCESS.md` | 智能体构建关键过程文档 |
| `docs/PITFALLS_AND_SOLUTIONS.md` | 踩过的坑与解决方案 |
| `docs/RESUME_AND_PORTFOLIO.md` | 项目介绍与简历材料 |
| `docs/LumiaOCR-v1.0-项目介绍.html` | 可离线打开的项目介绍 HTML |

## 注意事项

GitHub 仓库不包含本地模型权重、用户上传文件、运行日志、导出结果和前端依赖目录。以下内容已通过 `.gitignore` 排除：

- `models/`
- `third_party/`
- `frontend/node_modules/`
- `frontend/dist/`
- `uploads/`
- `exports/`
- `*.log`
- `__pycache__/`

如需运行 Dolphin-v2、MinerU 等重模型，请根据本机硬件和依赖环境单独安装模型文件。
