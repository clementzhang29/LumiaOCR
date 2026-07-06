<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { useMessage } from "naive-ui"
import {
  NButton,
  NCheckbox,
  NEmpty,
  NIcon,
  NInput,
  NProgress,
  NSelect,
  NSpace,
  NTag,
  NUpload,
} from "naive-ui"
import {
  Chatbubbles,
  CloudUpload,
  DocumentText,
  Download,
  GridOutline,
  Images,
  Language,
  Layers,
  Refresh,
  Send,
  Sparkles,
} from "@vicons/ionicons5"
import api from "../api"
import { useAppStore } from "../stores/app"

const message = useMessage()
const store = useAppStore()

const status = ref({ documents: [], tasks: [], chunk_count: 0, llm_enabled: false })
const files = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadPhase = ref("idle")
const uploadStartedAt = ref(0)
const nowTick = ref(Date.now())
const strategy = ref("auto")
const preferredEngine = ref("")
const selectedDocIds = ref([])
const question = ref("")
const asking = ref(false)
const messages = ref([
  {
    role: "agent",
    text: "上传一个或多个 PDF 后，我会自动完成 OCR、写入知识库，然后你可以直接对 OCR 后的文档提问。",
  },
])
const citations = ref([])
let timer = null
let clock = null

const actionChips = [
  { key: "summary", label: "总结全文", icon: Sparkles },
  { key: "translate_zh", label: "翻译为中文", icon: Language },
  { key: "tables", label: "提取表格", icon: GridOutline },
  { key: "figures", label: "整理图片素材", icon: Images },
  { key: "outline", label: "学术结构重排", icon: Layers },
  { key: "materials", label: "素材整合", icon: DocumentText },
]

const strategyOptions = [
  { value: "auto", label: "自动路由" },
  { value: "single", label: "固定引擎" },
]

const engineOptions = computed(() => [
  { label: "自动选择最适合的 OCR 模型", value: "" },
  ...store.engines.map((engine) => ({
    label: `${engine.name}${engine.available ? "" : "（未就绪）"}`,
    value: engine.id || engine.name,
    disabled: !engine.available,
  })),
])

const sortedTasks = computed(() =>
  status.value.tasks.slice().sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)),
)

const runningTasks = computed(() =>
  sortedTasks.value.filter((task) => ["queued", "analyzing", "converting"].includes(task.status)),
)

const completedTasks = computed(() => sortedTasks.value.filter((task) => task.status === "completed"))

const selectedDocCount = computed(() => selectedDocIds.value.length || status.value.documents.length)

const uploadElapsed = computed(() => {
  if (!uploading.value || !uploadStartedAt.value) return 0
  return Math.max(0, Math.round((nowTick.value - uploadStartedAt.value) / 1000))
})

const overallProgress = computed(() => {
  if (uploading.value) {
    if (uploadProgress.value < 100) return Math.max(2, Math.round(uploadProgress.value * 0.42))
    const waiting = Math.min(18, Math.floor(uploadElapsed.value * 1.8))
    return Math.min(60, 42 + waiting)
  }
  if (runningTasks.value.length) {
    const total = runningTasks.value.reduce((sum, task) => sum + smartProgress(task), 0)
    return Math.round(total / runningTasks.value.length)
  }
  if (completedTasks.value.length || status.value.documents.length) return 100
  return 0
})

const overallLabel = computed(() => {
  if (uploading.value && uploadProgress.value < 100) return "正在把文件传到本地服务"
  if (uploading.value) return "文件已到达服务端，正在保存并创建 OCR 队列"
  if (runningTasks.value.length) return `正在处理 ${runningTasks.value.length} 个 OCR 任务`
  if (completedTasks.value.length) return "OCR 已完成，可开始问答"
  return "等待上传文档"
})

const processFeed = computed(() => {
  const rows = []
  if (uploading.value) {
    rows.push({
      time: "now",
      title: uploadProgress.value < 100 ? "上传接收" : "创建任务",
      message:
        uploadProgress.value < 100
          ? `浏览器正在传输文件，已完成 ${uploadProgress.value}%`
          : `文件已传完，服务端正在写入磁盘并创建 OCR 任务，已等待 ${uploadElapsed.value} 秒`,
    })
  }
  for (const task of sortedTasks.value) {
    const events = (task.events || []).slice(-4)
    if (!events.length) {
      rows.push({ time: task.created_at, title: task.filename, message: task.stage_message || task.status })
      continue
    }
    for (const event of events.reverse()) {
      rows.push({
        time: event.time,
        title: task.filename,
        message: event.message,
      })
    }
  }
  return rows.slice(0, 18)
})

function smartProgress(task) {
  const raw = Number(task.progress || 0)
  if (task.status === "completed") return 100
  if (task.status === "failed") return raw || 100
  const created = new Date(task.created_at || Date.now()).getTime()
  const elapsed = Math.max(0, (nowTick.value - created) / 1000)
  const pages = Number(task.analysis?.page_count || 0)
  const estimatedSeconds = Math.max(90, Math.min(1800, (pages || 60) * 4.8))
  let estimated = raw
  if (task.status === "queued") estimated = Math.max(raw, Math.min(12, 4 + elapsed * 0.6))
  if (task.status === "analyzing") estimated = Math.max(raw, Math.min(28, 12 + elapsed * 0.7))
  if (task.status === "converting") {
    const conversionBase = 45
    const conversionGain = Math.min(38, (elapsed / estimatedSeconds) * 38)
    estimated = Math.max(raw, conversionBase + conversionGain)
  }
  return Math.max(0, Math.min(96, Math.round(estimated)))
}

function stageLabel(task) {
  if (task.status === "queued") return "排队中"
  if (task.status === "analyzing") return "文档体检"
  if (task.status === "converting") return "OCR 识别"
  if (task.status === "completed") return "已入库"
  if (task.status === "failed") return "失败"
  return task.status || "未知"
}

function formatTime(value) {
  if (!value || value === "now") return "现在"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(11, 19)
  return date.toLocaleTimeString("zh-CN", { hour12: false })
}

async function loadStatus() {
  const { data } = await api.agent.documents()
  status.value = data
  const valid = new Set(data.documents.map((doc) => doc.id))
  selectedDocIds.value = selectedDocIds.value.filter((id) => valid.has(id))
}

function handleFileChange({ fileList }) {
  files.value = fileList.map((item) => item.file).filter(Boolean)
}

function formatSize(bytes) {
  if (!bytes) return "0 MB"
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function uploadForOcr() {
  if (!files.value.length) {
    message.warning("请先选择 PDF 文档")
    return
  }
  uploading.value = true
  uploadPhase.value = "uploading"
  uploadStartedAt.value = Date.now()
  uploadProgress.value = 0
  try {
    const { data } = await api.agent.upload(files.value, strategy.value, preferredEngine.value, (progress) => {
      uploadProgress.value = progress
      if (progress >= 100) uploadPhase.value = "creating"
    })
    messages.value.push({
      role: "agent",
      text: `已创建 ${data.tasks.length} 个 OCR 任务。现在会持续刷新智能预估进度，完成后自动进入问答知识库。`,
    })
    files.value = []
    await loadStatus()
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || "上传失败")
  } finally {
    uploading.value = false
    uploadPhase.value = "idle"
  }
}

function selectedDocsPayload() {
  return selectedDocIds.value.length ? selectedDocIds.value : null
}

async function runAction(action, customQuestion = "") {
  if (!status.value.chunk_count) {
    message.warning("请先完成至少一个 OCR 文档入库")
    return
  }
  const chip = actionChips.find((item) => item.key === action)
  const prompt = customQuestion.trim()
  messages.value.push({ role: "user", text: prompt || chip?.label || action })
  asking.value = true
  citations.value = []
  try {
    const { data } = await api.agent.action({
      action,
      question: prompt,
      doc_ids: selectedDocsPayload(),
      top_k: 6,
    })
    messages.value.push({ role: "agent", text: data.answer, usedLlm: data.used_llm })
    citations.value = data.citations || []
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || "智能体处理失败")
  } finally {
    asking.value = false
  }
}

async function ask() {
  const q = question.value.trim()
  if (!q) {
    message.warning("请输入要问 OCR 文档的问题")
    return
  }
  question.value = ""
  await runAction("question", q)
}

function toggleDoc(docId, checked) {
  selectedDocIds.value = checked
    ? [...selectedDocIds.value, docId]
    : selectedDocIds.value.filter((id) => id !== docId)
}

function exportMarkdown() {
  const docTask = completedTasks.value.find((task) => !selectedDocIds.value.length || selectedDocIds.value.includes(task.rag_doc_id || task.id))
  if (!docTask) {
    message.warning("请选择一个已完成 OCR 的文档")
    return
  }
  window.open(api.download(docTask.id), "_blank")
}

onMounted(async () => {
  await loadStatus()
  timer = window.setInterval(loadStatus, 1500)
  clock = window.setInterval(() => {
    nowTick.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  if (clock) window.clearInterval(clock)
})
</script>

<template>
  <div class="agent-page rise-in">
    <div class="agent-head">
      <div>
        <p class="eyebrow">OCR Document Agent</p>
        <h1 class="section-title">OCR 智能体工作台</h1>
        <p class="section-kicker">
          多文档上传后自动 OCR、自动入库，并对 OCR 后的文档进行问答、翻译、表格提取和素材整合。
        </p>
      </div>
      <div class="agent-status">
        <div class="status-pill" :class="{ muted: !status.llm_enabled }">
          <span class="dot"></span>
          {{ status.llm_enabled ? "已接入大模型" : "本地检索模式" }}
        </div>
        <NButton secondary size="small" @click="loadStatus">
          <template #icon><NIcon><Refresh /></NIcon></template>
          刷新
        </NButton>
      </div>
    </div>

    <section class="panel panel-pad agent-live-strip">
      <div class="live-title">
        <div>
          <strong>{{ overallLabel }}</strong>
          <p class="microcopy">
            这是智能预估进度：真实 OCR 引擎可能按页、按布局、按文字识别分阶段推进，页面会结合后端事件实时调整。
          </p>
        </div>
        <span>{{ overallProgress }}%</span>
      </div>
      <NProgress :percentage="overallProgress" :height="9" :processing="uploading || !!runningTasks.length" />
      <div class="live-feed" v-if="processFeed.length">
        <div v-for="(row, index) in processFeed" :key="`${row.time}-${row.message}-${index}`" class="live-feed-row">
          <span>{{ formatTime(row.time) }}</span>
          <strong>{{ row.title }}</strong>
          <p>{{ row.message }}</p>
        </div>
      </div>
      <div v-else class="live-feed-empty">选择 PDF 后，这里会实时显示：上传接收、任务创建、文档体检、OCR 识别、质量评分、自动入库。</div>
    </section>

    <div class="agent-grid">
      <section class="panel panel-pad agent-upload-panel">
        <div class="panel-title-row">
          <div>
            <h2 class="subhead">上传并 OCR</h2>
            <p class="section-kicker">支持一次选择多个 PDF。完成后自动进入右侧知识库，不需要再手动上传 Markdown。</p>
          </div>
          <NTag type="info" :bordered="false">自动入库</NTag>
        </div>

        <NUpload
          :default-upload="false"
          multiple
          :show-file-list="false"
          accept="application/pdf,.pdf"
          @change="handleFileChange"
        >
          <div class="upload-zone agent-dropzone">
            <div class="upload-inner">
              <div class="upload-icon">
                <NIcon size="30"><CloudUpload /></NIcon>
              </div>
              <strong>{{ files.length ? `已选择 ${files.length} 个文档` : "拖入 PDF，或点击选择文件" }}</strong>
              <span class="microcopy">上传到 100% 只代表文件传完；下方总进度会继续显示 OCR 智能预估和关键事件。</span>
            </div>
          </div>
        </NUpload>

        <div v-if="files.length" class="file-list">
          <div v-for="file in files" :key="file.name" class="file-mini">
            <DocumentText class="mini-icon" />
            <span>{{ file.name }}</span>
            <small>{{ formatSize(file.size) }}</small>
          </div>
        </div>

        <div class="agent-config">
          <div>
            <label class="field-label">处理策略</label>
            <NSelect v-model:value="strategy" :options="strategyOptions" />
          </div>
          <div>
            <label class="field-label">首选 OCR 模型</label>
            <NSelect v-model:value="preferredEngine" :options="engineOptions" filterable />
          </div>
        </div>

        <div class="action-bar">
          <span class="microcopy">不配置大模型也可以 OCR 和本地检索；配置后问答、翻译和整理会更自然。</span>
          <NButton type="primary" size="large" :loading="uploading" :disabled="!files.length" @click="uploadForOcr">
            {{ uploading ? "正在接收/建队列" : "开始 OCR 入库" }}
          </NButton>
        </div>
      </section>

      <section class="panel panel-pad knowledge-panel">
        <div class="panel-title-row">
          <div>
            <h2 class="subhead">文档知识库</h2>
            <p class="section-kicker">{{ status.documents.length }} 个文档，{{ status.chunk_count }} 个检索片段。勾选后只问选中文档。</p>
          </div>
          <NTag type="success" :bordered="false">{{ selectedDocCount }} 个生效</NTag>
        </div>

        <div v-if="status.documents.length" class="doc-list">
          <label v-for="doc in status.documents" :key="doc.id" class="doc-card">
            <NCheckbox
              :checked="selectedDocIds.includes(doc.id)"
              @update:checked="(checked) => toggleDoc(doc.id, checked)"
            />
            <div>
              <strong>{{ doc.filename }}</strong>
              <span>{{ doc.source === "ocr" ? "OCR 自动入库" : "手动入库" }} · {{ doc.chunks }} chunks · {{ doc.chars }} 字符</span>
            </div>
          </label>
        </div>
        <NEmpty v-else description="还没有 OCR 文档入库" />
      </section>

      <section class="process-console agent-console">
        <div class="console-head">
          <strong>任务队列</strong>
          <span v-if="runningTasks.length" class="pulse">运行中</span>
          <span v-else>等待任务</span>
        </div>
        <div class="console-body">
          <div v-if="!sortedTasks.length" class="console-empty">队列为空。上传 PDF 后会出现每个任务的智能预估进度。</div>
          <template v-for="task in sortedTasks" :key="task.id">
            <div class="task-line">
              <div>
                <strong>{{ task.filename }}</strong>
                <span>{{ stageLabel(task) }} · {{ task.stage_message || task.status }}</span>
              </div>
              <NTag size="small" :type="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'info'" :bordered="false">
                {{ smartProgress(task) }}%
              </NTag>
            </div>
            <NProgress :percentage="smartProgress(task)" :height="6" :processing="['queued','analyzing','converting'].includes(task.status)" />
          </template>
        </div>
      </section>

      <section class="panel panel-pad chat-panel">
        <div class="panel-title-row">
          <div>
            <h2 class="subhead">对 OCR 后文档提问</h2>
            <p class="section-kicker">先点常用操作，也可以输入自己的问题。回答会附带引用片段。</p>
          </div>
          <NIcon size="24" color="#0f9f8f"><Chatbubbles /></NIcon>
        </div>

        <div class="chip-row">
          <NButton
            v-for="chip in actionChips"
            :key="chip.key"
            secondary
            :disabled="asking || !status.chunk_count"
            @click="runAction(chip.key)"
          >
            <template #icon><NIcon><component :is="chip.icon" /></NIcon></template>
            {{ chip.label }}
          </NButton>
          <NButton secondary :disabled="!completedTasks.length" @click="exportMarkdown">
            <template #icon><NIcon><Download /></NIcon></template>
            导出 Markdown
          </NButton>
        </div>

        <div class="chat-window">
          <div v-for="(item, index) in messages" :key="index" class="chat-bubble" :class="item.role">
            <p>{{ item.text }}</p>
            <span v-if="item.usedLlm === false">本地检索回答</span>
          </div>
          <div v-if="asking" class="chat-bubble agent thinking">
            <p>正在检索 OCR 片段并组织回答...</p>
          </div>
        </div>

        <NSpace vertical size="medium">
          <NInput
            v-model:value="question"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 7 }"
            placeholder="例如：这几篇文档的实验方法有什么差异？表格里有哪些关键数据？请按中文汇报稿整理。"
            @keydown.ctrl.enter.prevent="ask"
          />
          <NButton type="primary" size="large" :loading="asking" :disabled="!status.chunk_count" @click="ask">
            <template #icon><NIcon><Send /></NIcon></template>
            发送问题
          </NButton>
        </NSpace>

        <div v-if="citations.length" class="citation-list agent-citations">
          <h3>引用片段</h3>
          <div v-for="item in citations" :key="item.chunk_id" class="citation-card">
            <div class="citation-head">
              <strong>[{{ item.rank }}] {{ item.filename }}</strong>
              <NTag size="small" :bordered="false">score {{ item.score }}</NTag>
            </div>
            <p>{{ item.text }}</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
