<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { marked } from "marked"
import {
  NAlert,
  NButton,
  NEmpty,
  NIcon,
  NProgress,
  NSkeleton,
  NTag,
} from "naive-ui"
import {
  ArrowBack,
  CheckmarkCircle,
  CloseCircle,
  Download,
  Hourglass,
  OpenOutline,
  Terminal,
  Time,
} from "@vicons/ionicons5"
import api from "../api"

const route = useRoute()
const router = useRouter()
const taskId = route.params.id

const task = ref(null)
const error = ref("")
const polling = ref(true)
const markdownHtml = ref("")

const progress = computed(() => Math.max(0, Math.min(100, task.value?.progress || 0)))
const isRunning = computed(() => ["queued", "analyzing", "converting"].includes(task.value?.status))
const isDone = computed(() => task.value?.status === "completed")
const isFailed = computed(() => task.value?.status === "failed")

const statusLabel = computed(() => {
  const status = task.value?.status
  if (status === "completed") return "转换完成"
  if (status === "failed") return "转换失败"
  if (status === "analyzing") return "正在体检文档"
  if (status === "converting") return "正在 OCR 转换"
  return "等待调度"
})

const statusType = computed(() => {
  if (isDone.value) return "success"
  if (isFailed.value) return "error"
  return "info"
})

const events = computed(() => {
  const list = task.value?.events || []
  if (list.length) return list
  return [{ time: task.value?.created_at, stage: "queued", message: "任务已创建" }]
})

const analysisRows = computed(() => {
  const analysis = task.value?.analysis
  if (!analysis) return []
  return [
    ["文档类型", analysis.doc_type || "unknown"],
    ["页数", analysis.page_count ?? "-"],
    ["语言", analysis.language_hint === "zh" ? "中文" : analysis.language_hint || "-"],
    ["扫描件", analysis.is_scanned ? "是" : "否"],
    ["推荐引擎", analysis.recommended_engine || "-"],
  ]
})

function formatTime(value) {
  if (!value) return "--:--:--"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(11, 19) || "--:--:--"
  return date.toLocaleTimeString("zh-CN", { hour12: false })
}

async function poll() {
  while (polling.value) {
    try {
      const { data } = await api.status(taskId)
      task.value = data

      if (data.status === "completed") {
        polling.value = false
        const result = await api.result(taskId)
        task.value = { ...task.value, ...result.data }
        if (task.value.markdown) {
          markdownHtml.value = marked.parse(task.value.markdown, { breaks: true, gfm: true })
        }
      } else if (data.status === "failed") {
        polling.value = false
      }
    } catch (requestError) {
      error.value = requestError.response?.data?.detail || requestError.message
      polling.value = false
    }

    if (polling.value) {
      await new Promise((resolve) => setTimeout(resolve, 1200))
    }
  }
}

function download() {
  window.open(api.download(taskId), "_blank")
}

onMounted(poll)
onUnmounted(() => {
  polling.value = false
})
</script>

<template>
  <div class="rise-in">
    <div class="hero-line">
      <div>
        <h1 class="section-title">任务结果</h1>
        <p class="section-kicker">过程、评分和 Markdown 输出集中在同一页。</p>
      </div>
      <div class="toolbar">
        <NButton secondary @click="router.push('/')">
          <template #icon>
            <NIcon><ArrowBack /></NIcon>
          </template>
          新任务
        </NButton>
        <NButton type="primary" :disabled="!isDone || !task?.markdown" @click="download">
          <template #icon>
            <NIcon><Download /></NIcon>
          </template>
          下载 Markdown
        </NButton>
      </div>
    </div>

    <div v-if="!task && !error" class="panel panel-pad loading-panel">
      <NSkeleton height="32px" width="220px" />
      <NSkeleton height="14px" width="360px" />
      <NSkeleton height="180px" />
    </div>

    <NAlert v-else-if="error" type="error" :bordered="false">{{ error }}</NAlert>

    <div v-else class="result-grid">
      <aside class="stack-column">
        <section class="panel panel-pad stage-card">
          <div class="panel-title-row">
            <div>
              <h2 class="subhead">{{ statusLabel }}</h2>
              <p class="section-kicker">{{ task.stage_message || "正在等待新的处理状态" }}</p>
            </div>
            <NTag :type="statusType" :bordered="false">
              {{ task.status }}
            </NTag>
          </div>

          <NProgress
            :percentage="progress"
            :height="9"
            :processing="isRunning"
            :status="isFailed ? 'error' : isDone ? 'success' : undefined"
            style="margin-top: 16px"
          />

          <div class="metric-strip">
            <div class="metric">
              <div class="metric-value">{{ progress }}%</div>
              <div class="metric-label">当前进度</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ task.engine_used || "-" }}</div>
              <div class="metric-label">使用引擎</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ task.processing_time ? task.processing_time.toFixed(1) : "-" }}</div>
              <div class="metric-label">处理秒数</div>
            </div>
          </div>
        </section>

        <section class="process-console">
          <div class="console-head">
            <strong>
              <NIcon style="vertical-align: -2px"><Terminal /></NIcon>
              处理过程
            </strong>
            <span v-if="isRunning" class="pulse">运行中</span>
            <span v-else>{{ isDone ? "完成" : "停止" }}</span>
          </div>
          <div class="console-body">
            <div v-for="event in events" :key="`${event.time}-${event.stage}-${event.message}`" class="console-row">
              <span class="console-time">{{ formatTime(event.time) }}</span>
              <span class="console-message">{{ event.message }}</span>
            </div>
          </div>
        </section>

        <section class="panel panel-pad" v-if="analysisRows.length">
          <h2 class="subhead">文档体检</h2>
          <div class="summary-list">
            <div v-for="[label, value] in analysisRows" :key="label" class="summary-row">
              <span>{{ label }}</span>
              <strong>{{ value }}</strong>
            </div>
          </div>
        </section>

        <NAlert v-if="isFailed" type="error" :bordered="false">
          {{ task.error || "任务失败，请检查文件或引擎环境。" }}
        </NAlert>
      </aside>

      <section class="panel panel-pad preview-panel">
        <div class="panel-title-row">
          <div>
            <h2 class="subhead">Markdown 预览</h2>
            <p class="section-kicker">
              {{ task.markdown ? `${task.markdown.length} 个字符` : "转换完成后会在这里出现。" }}
            </p>
          </div>
          <div class="toolbar">
            <NTag v-if="task.quality_score !== undefined" :type="task.quality_score >= 0.85 ? 'success' : 'warning'" :bordered="false">
              质量 {{ Math.round(task.quality_score * 100) }}
            </NTag>
            <NButton v-if="isDone && task.markdown" size="small" secondary @click="download">
              <template #icon>
                <NIcon><OpenOutline /></NIcon>
              </template>
              导出
            </NButton>
          </div>
        </div>

        <div v-if="markdownHtml" class="markdown-preview" v-html="markdownHtml"></div>
        <div v-else-if="isRunning" class="empty-preview">
          <NIcon size="42" color="#335cff">
            <Hourglass />
          </NIcon>
          <strong>正在生成文档结构</strong>
          <span>识别完成后会自动刷新。</span>
        </div>
        <div v-else-if="isFailed" class="empty-preview error">
          <NIcon size="42" color="#c2415a">
            <CloseCircle />
          </NIcon>
          <strong>没有生成结果</strong>
          <span>请查看左侧错误信息。</span>
        </div>
        <NEmpty v-else description="暂无内容" />

        <div v-if="isDone" class="completion-band">
          <NIcon color="#0f9f8f" size="20">
            <CheckmarkCircle />
          </NIcon>
          <span>转换完成，可以继续下载或发起新任务。</span>
        </div>
        <div v-else-if="isRunning" class="completion-band soft">
          <NIcon color="#335cff" size="20">
            <Time />
          </NIcon>
          <span>{{ task.stage_message || "系统正在处理。" }}</span>
        </div>
      </section>
    </div>
  </div>
</template>
