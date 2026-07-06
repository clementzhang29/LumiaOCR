# 项目介绍与简历材料

作者：张春  
整理：AI 根据项目文件整理生成  
更新时间：2026-07-07（Asia/Shanghai）
版本：v1.0  
项目仓库：https://github.com/clementzhang29/LumiaOCR

## 1. 一句话项目介绍

LumiaOCR 是一个基于 FastAPI + Vue 3 构建的智能文档解析与 RAG 问答系统，支持多 OCR 模型路由、复杂科研论文图文表格混排解析、OCR 后知识库问答和布局感知 HTML 导出。

## 2. 简历版项目描述

独立设计并实现 LumiaOCR v1.0 智能文档解析与知识问答系统，基于 FastAPI + Vue 3 构建 Web 工作台，集成 Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat 等多 OCR/文档解析引擎，支持 PDF 文档自动体检、模型路由、复杂科研论文图文表格混排解析、Markdown/HTML 输出、任务进度可视化及 OCR 结果自动入库。系统内置轻量 RAG 检索与 OpenAI-compatible LLM Provider 接入能力，可对 OCR 后多文档进行问答、摘要、翻译、表格提取、图片素材整理和学术结构重排。项目中解决了大文件 OCR 阻塞 Web 轮询、上传进度与实际处理进度割裂、科研论文表格/图片排版还原不足等问题，通过后台线程化任务、智能预估进度、过程消息反馈和布局感知 HTML 导出提升了可用性与交付质量。

## 3. 简历项目条目

项目名称：LumiaOCR v1.0 智能文档解析与知识问答系统  
项目角色：独立开发 / 产品设计 / AI 协作实现  
技术栈：Python、FastAPI、Vue 3、Vite、Naive UI、PyMuPDF、Dolphin-v2、MinerU、Marker、Docling、Surya、PaddleOCR、Nougat、OpenAI-compatible API、RAG

项目职责：

- 设计六层 OCR 智能体架构，覆盖文件接入、文档体检、模型路由、OCR 解析、纠错排版和知识交互。
- 构建 FastAPI 后端，提供 OCR 任务、模型 Provider、RAG 文档和聊天问答接口。
- 构建 Vue 3 Web 工作台，实现多 PDF 上传、任务队列、智能进度、过程消息和 OCR 后问答交互。
- 接入 Dolphin-v2 等多种 OCR/文档解析引擎，针对科研论文图文表格混排进行专门增强。
- 实现 OCR Markdown 自动入库、轻量检索、LLM 可选问答和无 LLM fallback。
- 编写布局感知 HTML 导出脚本，提升 OCR 输出的阅读和展示效果。
- 完成项目文档、AI 交接文档、踩坑复盘和 GitHub 交付。

项目成果：

- 支持多文档 OCR 与 OCR 后 RAG 问答的一体化工作流。
- 解决上传完成但 OCR 仍在处理导致的用户等待不确定问题。
- 通过后台线程化任务避免长耗时 OCR 阻塞接口轮询。
- 通过模型路由提升复杂科研论文解析能力。
- 输出 Markdown、HTML 和项目级介绍文档，具备展示和二次开发价值。

## 4. 面试讲解版本

这个项目的出发点是解决复杂 PDF 文档从 OCR 到知识利用的完整链路。传统 OCR 工具往往只能输出文字，但科研论文和扫描件真正难的是版面、表格、图片、公式和阅读顺序。我的方案是先做文档体检，根据文档特征进行模型路由，然后把 OCR 结果经过纠错、清洗和排版后自动进入 RAG 知识库。

后端使用 FastAPI 构建任务接口和模型 Provider 接口，OCR Pipeline 负责调度不同引擎。前端使用 Vue 3 和 Naive UI 构建工作台，重点优化了用户等待体验：上传完成后继续显示 OCR 阶段的智能进度和处理消息。后来我又把问答入口改成“对 OCR 后文档提问”，让 OCR 结果能直接用于摘要、翻译、表格提取和素材整理。

项目中比较关键的技术问题包括长耗时 OCR 阻塞事件循环、科研论文表格和图片还原不足、GitHub 交付时大模型权重不能入仓库等。对应方案是后台线程化执行 OCR、接入 Dolphin-v2 并增强 HTML 导出，以及通过 `.gitignore` 排除模型、依赖、上传文件和运行缓存。

## 5. 项目亮点关键词

- 多模型 OCR 路由。
- 科研论文复杂版面解析。
- OCR 后 RAG。
- 智能进度与过程消息。
- OpenAI-compatible Provider。
- 布局感知 HTML 导出。
- FastAPI + Vue 3 全栈实现。
- AI 协作开发与完整交付文档。


