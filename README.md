# OCR-Harness

六层 OCR 文档处理系统，用 FastAPI + Vue 3 做成可直接使用的 WebUI。系统集成 Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat 七个 OCR/文档解析引擎，并可在界面里配置 OpenAI 兼容 API Provider，用于表格、公式和阅读顺序校正。

## 六层流程

```text
PDF 接入
  -> 文档体检
  -> 智能路由
  -> 七引擎 OCR/文档解析
  -> LLM 语义校正
  -> 质量验收与 Markdown 输出
```

处理过程中，前端结果页会持续显示任务状态、阶段消息、进度条和事件日志，避免用户等待时没有反馈。

## WebUI

- `转换工作台`：上传 PDF，选择智能路由或固定引擎，查看六层流水线和七大引擎状态。
- `任务结果`：展示实时处理过程、文档体检结果、质量评分、Markdown 预览和下载入口。
- `API 设置`：选择常见 Provider 模板，填入 API 地址、Key 和模型，保存后即可用于 OCR 校正层。

API Key 当前保存在服务进程内存中，不写入明文文件；服务重启后需要重新配置。

## Dolphin-v2 科研论文增强

项目新增 ByteDance Dolphin-v2 作为复杂科研论文专用解析引擎。它适合图文、表格、公式混排的论文 PDF，输出 JSON/Markdown，并保留阅读顺序和版面元素信息。

当前下载位置：

```text
third_party/Dolphin-master
models/dolphin-v2
```

新机器上可重新安装：

```powershell
scripts/install_dolphin.ps1
```

自动路由规则：

- `complex_scientific_paper` -> `dolphin`
- `scientific_paper` -> `dolphin`
- 如果 Dolphin 不可用或执行失败，会自动回退到 Docling、MinerU、Marker、Surya 等原有引擎。

## 启动

```powershell
python -m src.web.main
```

默认端口是 `8080`。如果端口被占用，可以指定新端口：

```powershell
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8090
```

打开：

```text
http://127.0.0.1:8080/
```

或使用你指定的端口，例如 `http://127.0.0.1:8090/`。

## 前端开发

本项目以前端 `npm` 为准，保留 `package-lock.json`。

```powershell
cd frontend
npm install
npm run dev
npm run build
```

生产构建输出到 `frontend/dist`，FastAPI 会挂载 `/assets` 并对 Vue History 路由做回退，刷新 `/providers`、`/result/:id` 不会 404。

## API

- `GET /api/health`：健康检查
- `GET /api/engines`：列出 OCR/文档解析引擎和可用状态
- `POST /api/convert`：上传 PDF 并创建 OCR 任务
- `GET /api/status/{task_id}`：查询任务状态、进度和事件日志
- `GET /api/result/{task_id}`：获取完成后的 Markdown 结果
- `GET /api/download/{task_id}`：下载 Markdown
- `GET /api/providers`：列出已配置 Provider
- `POST /api/providers`：注册 Provider
- `POST /api/providers/verify`：验证 Provider 连接

Swagger 文档：

```text
http://127.0.0.1:8080/docs
```

## 项目结构

```text
ocr-harness-v0.1.0/
├── config/                # 引擎配置
├── docs/                  # 项目介绍和安装文档
├── frontend/              # Vue 3 + Naive UI WebUI
├── models/                # 本地模型权重，含 Dolphin-v2
├── scripts/               # 安装脚本
├── src/
│   ├── correctors/        # 表格、公式、阅读顺序校正
│   ├── engines/           # 七个 OCR/文档解析引擎封装
│   ├── formatter/         # Markdown 清理
│   ├── llm/               # Provider 识别、路由和 Key 管理
│   ├── orchestrator/      # 文档分析与 Pipeline 调度
│   ├── qa/                # 质量评分
│   └── web/               # FastAPI 服务
├── tests/                 # 测试脚本与样例 PDF
├── third_party/           # Dolphin 上游仓库代码
├── uploads/               # 运行时上传目录
└── test_e2e.py
```

## 验证

```powershell
python -m compileall -q src test_e2e.py tests
python -B test_e2e.py
cd frontend
npm run build
```

HTTP 端到端验证可用 `POST /api/convert` 上传 PDF，再轮询 `/api/status/{task_id}`。完成后状态中会包含 `events`、`engine_used`、`quality_score` 和 `markdown`。
