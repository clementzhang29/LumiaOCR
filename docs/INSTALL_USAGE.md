# OCR-Harness 安装使用文档

## 环境要求

- Windows 10/11
- Python 3.10 及以上，推荐 Python 3.12
- Node.js 18 及以上，用于重新构建前端
- 可选：NVIDIA GPU 和 CUDA 环境

如果已经在当前机器上完成模型和依赖部署，可以直接进入“启动服务”。

## Python 依赖

项目使用本地源码方式运行。进入项目目录：

```powershell
cd C:\Users\35160\Desktop\ocr-harness-v0.1.0
```

按需安装 OCR 相关依赖：

```powershell
pip install fastapi uvicorn python-multipart pydantic
pip install magic-pdf marker-pdf docling surya-ocr paddleocr nougat-ocr
```

如果只想先验证 Web 服务和前端页面，至少需要：

```powershell
pip install fastapi uvicorn python-multipart pydantic
```

具体 OCR 引擎能否运行取决于对应包、模型权重和本机硬件环境。

## Dolphin-v2 科研论文增强模型

Dolphin-v2 已作为复杂科研论文专用引擎接入路由，适合图文、表格、公式混排 PDF。

当前项目默认路径：

```text
third_party/Dolphin-master
models/dolphin-v2
```

如需在新机器重新下载：

```powershell
scripts/install_dolphin.ps1
```

如果你把 Dolphin 仓库或模型移动到别处，可设置：

```powershell
$env:DOLPHIN_REPO_DIR="D:\models\Dolphin-master"
$env:DOLPHIN_MODEL_DIR="D:\models\dolphin-v2"
```

注意：Dolphin-v2 权重约 7.5GB，CPU 可运行但会很慢，建议 GPU 环境。

## 前端依赖与构建

交付包内已经包含 `frontend/dist`，通常不需要重新构建。需要修改前端时再执行：

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

开发服务会代理 `/api` 到后端 `http://localhost:8080`。

## 启动服务

默认启动：

```powershell
python -m src.web.main
```

默认地址：

```text
http://127.0.0.1:8080/
```

如果 8080 被占用，可以换端口：

```powershell
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8090
```

然后打开：

```text
http://127.0.0.1:8090/
```

## WebUI 使用流程

1. 打开“转换工作台”。
2. 选择或拖入 PDF 文件。
3. 选择处理策略：
   - 智能路由：系统根据文档体检结果自动选择引擎。
   - 固定引擎：使用指定的首选 OCR 引擎。
4. 点击“开始转换”。
5. 进入“任务结果”页，查看进度、处理事件和 Markdown 预览。
6. 转换完成后点击“下载 Markdown”。

## API Provider 配置

打开“API 设置”页：

1. 选择 OpenAI、DeepSeek、智谱 GLM、Kimi、Qwen 或 Claude 模板。
2. 填入名称、API 地址、API Key 和模型。
3. 点击“保存”。
4. 可点击“检查连接”验证 Provider。

说明：

- API Key 当前只保存在服务进程内存中。
- 服务重启后需要重新配置。
- 没有配置 API Provider 时，基础 OCR 仍可使用，只会跳过 LLM 校正层。

## 常用 API

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
```

Swagger 文档：

```text
http://127.0.0.1:8080/docs
```

## 验证命令

后端语法检查：

```powershell
python -m compileall -q src test_e2e.py tests
```

直接 Pipeline 端到端测试：

```powershell
python -B test_e2e.py
```

前端构建：

```powershell
cd frontend
npm run build
```

## 打包说明

推荐打包时排除：

- `frontend/node_modules`
- `server_runtime.log`
- `server_runtime.err.log`
- `uploads/*`
- `__pycache__`

交付包只需要包含源码、`frontend/dist`、配置、测试样例和文档即可。
