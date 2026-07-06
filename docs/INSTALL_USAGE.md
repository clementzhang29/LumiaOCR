# OCR Agent 安装与使用文档

作者：张春  
整理：AI 根据项目文件整理生成  
更新时间：2026-07-06（Asia/Shanghai）

## 1. 环境要求

- Windows 10/11。
- Python 3.10+，推荐 Python 3.12。
- Node.js 18+，用于重新安装或构建前端。
- 可选：NVIDIA GPU + CUDA。复杂 OCR 模型在 CPU 上可运行但速度较慢。

## 2. 获取项目

```powershell
git clone https://github.com/clementzhang29/ocr-agent-document-rag.git
cd ocr-agent-document-rag
```

如果使用本机已整理好的目录：

```powershell
cd C:\Users\35160\Desktop\ocr-harness-v0.1.0
```

## 3. Python 依赖

基础 Web 服务依赖：

```powershell
pip install fastapi uvicorn python-multipart pydantic pymupdf
```

按需安装 OCR 引擎依赖：

```powershell
pip install marker-pdf docling surya-ocr paddleocr nougat-ocr
```

MinerU / magic-pdf、Dolphin-v2 等模型依赖较重，建议根据硬件环境单独安装和调试。

## 4. Dolphin-v2 模型

Dolphin-v2 用于复杂科研论文、图文表格混排和学术 PDF 增强解析。项目默认查找：

```text
third_party/Dolphin-master
models/dolphin-v2
```

由于模型权重较大，GitHub 仓库不包含本地模型文件。新机器部署时需要重新下载或设置环境变量：

```powershell
$env:DOLPHIN_REPO_DIR="D:\models\Dolphin-master"
$env:DOLPHIN_MODEL_DIR="D:\models\dolphin-v2"
```

## 5. 前端依赖

```powershell
cd frontend
npm install
npm run build
cd ..
```

开发模式：

```powershell
cd frontend
npm run dev
```

## 6. 启动后端

默认启动：

```powershell
python -m src.web.main
```

访问：

```text
http://127.0.0.1:8080/
```

如果 8080 端口被占用：

```powershell
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8091
```

访问：

```text
http://127.0.0.1:8091/
```

## 7. 使用流程

1. 打开 Web UI。
2. 进入 OCR 智能体或 RAG 工作台。
3. 上传一个或多个 PDF。
4. 系统自动创建任务并分析文档类型。
5. 前端显示智能预估进度和实时过程消息。
6. OCR 完成后查看 Markdown 结果。
7. 在问答区基于 OCR 后文档提问。
8. 使用快捷标签执行翻译、摘要、表格提取、素材整理或导出。

## 8. API Provider 配置

进入 API 设置页，填写 OpenAI-compatible Provider：

- Provider 名称。
- Base URL，例如 `https://api.openai.com/v1`。
- API Key。
- 模型名称。

说明：

- OCR 主流程不强制依赖大模型。
- 配置 LLM 后，纠错、摘要、翻译和 RAG 回答效果会更好。
- 当前 Provider 主要保存在服务进程内存中，重启服务后需要重新配置。

## 9. 常用接口

```text
GET  /api/health
GET  /api/engines
POST /api/convert
GET  /api/status/{task_id}
GET  /api/result/{task_id}
GET  /api/download/{task_id}
GET  /api/providers
POST /api/providers
POST /api/providers/verify
POST /api/rag/upload
POST /api/rag/chat
GET  /api/rag/docs
```

Swagger 文档：

```text
http://127.0.0.1:8080/docs
```

## 10. 验证命令

后端语法检查：

```powershell
python -m compileall -q src test_e2e.py tests
```

前端构建：

```powershell
cd frontend
npm run build
```

Git 状态：

```powershell
git status --short --branch
```

## 11. GitHub 推送

当前仓库：

```text
https://github.com/clementzhang29/ocr-agent-document-rag
```

常用命令：

```powershell
git add .
git commit -m "Update project docs"
git push
```

## 12. 打包注意事项

不建议打包或上传：

- `models/`
- `third_party/`
- `frontend/node_modules/`
- `frontend/dist/`
- `uploads/`
- `exports/`
- `*.log`
- `__pycache__/`

这些目录通常包含模型权重、依赖、运行缓存、用户上传文件或生成结果，体积大且不适合进入公开仓库。
