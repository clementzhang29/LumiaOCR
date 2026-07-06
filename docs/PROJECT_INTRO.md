# OCR-Harness 项目介绍

## 项目定位

OCR-Harness 是一个面向 PDF 文档识别、结构化提取和 Markdown 输出的六层 OCR 系统。它把多个成熟 OCR 引擎、文档路由、质量评分和 LLM 校正组合成一个可操作的 WebUI 工作台，让用户可以上传 PDF 后直接获得可预览、可下载的 Markdown 结果。

项目适合以下场景：

- 扫描 PDF、论文 PDF、中文文档、英文技术文档的 OCR 转换
- 文档结构识别、阅读顺序修复、表格与公式校正
- 多 OCR 引擎效果对比和自动路由
- 本地部署的文档处理工作台

## 六层架构

```text
1. 文件接入
   接收 PDF，生成任务 ID，写入运行时上传目录。

2. 文档体检
   分析页数、文档类型、文本层、扫描特征、语言线索和推荐引擎。

3. 策略路由
   支持智能路由和固定引擎两种策略，决定使用哪个 OCR 引擎。

4. 六引擎 OCR
   集成 MinerU、Marker、Docling、Surya、PaddleOCR、Nougat。

5. LLM 语义校正
   配置 API Provider 后，可对表格、公式、阅读顺序进行增强校正。

6. 质量验收
   进行质量评分、Markdown 清理、结果预览和下载。
```

## 引擎矩阵

| 引擎 | 适用方向 | 说明 |
| --- | --- | --- |
| Dolphin-v2 | 复杂科研论文、图文表格公式混排 | 适合阅读顺序、表格、公式和版面元素解析 |
| MinerU | 论文、扫描件、公式与图表 | 适合复杂学术/扫描文档 |
| Marker | PDF 到 Markdown | 稳定的结构化转换 |
| Docling | 通用文档解析 | 适合结构抽取和通用 PDF |
| Surya | 版面结构、阅读顺序 | 适合复杂页面和多语言 OCR |
| PaddleOCR | 中文 OCR | 适合中文和轻量场景 |
| Nougat | 学术论文、LaTeX | 适合公式和论文类文档 |

## WebUI 设计

WebUI 由 Vue 3 + Naive UI 构建，分为三个核心页面：

- 转换工作台：上传 PDF、选择策略、查看六层流水线和引擎状态。
- 任务结果：展示实时进度、处理事件、质量评分、Markdown 预览和下载。
- API 设置：配置 OpenAI 兼容 API Provider，保存后用于 LLM 校正层。

结果页会持续轮询 `/api/status/{task_id}`，显示后端事件流，用户可以看到当前处理阶段，不会在转换过程中空等。

## 技术栈

- 后端：FastAPI、Uvicorn、Pydantic、异步任务
- 前端：Vue 3、Vite、Pinia、Vue Router、Naive UI、Ionicons
- OCR：Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat

## 科研论文增强路由

复杂科研论文会优先路由到 Dolphin-v2：

- `complex_scientific_paper`：含公式并伴随图片或表格的混排论文
- `scientific_paper`：普通公式/论文类 PDF

Dolphin-v2 不可用或执行失败时，Pipeline 会自动回退到 Docling、MinerU、Marker、Surya 等原有引擎，保证任务不因单一模型失败而中断。
- LLM：OpenAI 兼容接口自动识别与路由
- 输出：Markdown

## 目录概览

```text
ocr-harness-v0.1.0/
├── config/              # 引擎配置
├── docs/                # 项目介绍和安装使用文档
├── frontend/            # Vue WebUI
├── src/                 # 后端源码
│   ├── correctors/      # 表格、公式、阅读顺序校正
│   ├── engines/         # OCR 引擎封装
│   ├── formatter/       # Markdown 清理
│   ├── llm/             # Provider 管理和 LLM 路由
│   ├── orchestrator/    # 文档分析和 Pipeline
│   ├── qa/              # 质量评分
│   └── web/             # FastAPI Web 服务
├── tests/               # 测试样例和脚本
├── uploads/             # 运行时上传目录
├── README.md
└── test_e2e.py
```
