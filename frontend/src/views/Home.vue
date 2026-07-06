<script setup>
import { computed, ref } from "vue"
import { useRouter } from "vue-router"
import { useMessage } from "naive-ui"
import {
  NButton,
  NIcon,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NTag,
  NText,
  NUpload,
} from "naive-ui"
import {
  Analytics,
  CheckmarkCircle,
  CloudUpload,
  DocumentAttach,
  Flash,
  GitNetwork,
  LayersOutline,
  Reader,
  Rocket,
  Server,
  ShieldCheckmark,
} from "@vicons/ionicons5"
import api from "../api"
import { useAppStore } from "../stores/app"

const router = useRouter()
const message = useMessage()
const store = useAppStore()

const file = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const strategy = ref("auto")
const preferredEngine = ref("")

const strategyOptions = [
  { value: "auto", label: "智能路由" },
  { value: "single", label: "固定引擎" },
]

const pipelineLayers = [
  { icon: DocumentAttach, title: "文件接入", text: "PDF 入库、任务建档" },
  { icon: Analytics, title: "文档体检", text: "页数、文本层、扫描特征" },
  { icon: GitNetwork, title: "策略路由", text: "自动选择或锁定首选引擎" },
  { icon: LayersOutline, title: "七引擎 OCR", text: "Dolphin / Surya / MinerU / Marker / Docling / Paddle / Nougat" },
  { icon: ShieldCheckmark, title: "语义校正", text: "接入 API 后修复表格与顺序" },
  { icon: CheckmarkCircle, title: "质量验收", text: "评分、预览、Markdown 下载" },
]

const engineNotes = {
  dolphin: "复杂科研论文、图文表格公式混排",
  surya: "版面结构、阅读顺序、复杂页面",
  mineru: "论文、扫描件、公式与图表",
  marker: "PDF 到 Markdown 的稳定转换",
  docling: "通用文档解析与结构抽取",
  paddleocr: "中文 OCR 与轻量场景",
  nougat: "学术论文、LaTeX 与公式",
}

const engineOptions = computed(() => [
  { label: "自动选择最合适引擎", value: "" },
  ...store.engines.map((engine) => ({
    label: `${engine.name}${engine.available ? "" : "（未就绪）"}`,
    value: engine.id || engine.name,
    disabled: !engine.available,
  })),
])

const visibleEngines = computed(() =>
  store.engines.map((engine, index) => ({
    ...engine,
    index: index + 1,
    note: engineNotes[engine.id] || "可参与 OCR 路由",
  })),
)

const availableCount = computed(() => store.engines.filter((engine) => engine.available).length)
const providerReady = computed(() => store.providers.length > 0)

function handleFileChange({ file: uploadFile }) {
  file.value = uploadFile?.file || null
}

function formatSize(bytes) {
  if (!bytes) return "0 MB"
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function submit() {
  if (uploading.value) return
  if (!file.value) {
    message.error("请选择一个 PDF 文件")
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  try {
    const { data } = await api.convert(
      file.value,
      strategy.value,
      preferredEngine.value,
      (progress) => {
        uploadProgress.value = progress
      },
    )
    message.success("任务已创建，正在进入 OCR 流水线")
    router.push(`/result/${data.task_id}`)
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || "上传失败")
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="rise-in">
    <div class="hero-line">
      <div>
        <h1 class="section-title">六层 OCR 文档工作台</h1>
        <p class="section-kicker">上传 PDF，选择处理策略，系统会在七个 OCR/文档解析引擎与 LLM 校正层之间完成调度。</p>
      </div>
      <div class="status-pill" :class="{ muted: !providerReady }">
        <span class="dot"></span>
        {{ providerReady ? `已接入 ${store.providers.length} 个 API` : "OCR 可用，LLM 待接入" }}
      </div>
    </div>

    <div class="workspace-grid">
      <section class="panel panel-pad">
        <NUpload
          :default-upload="false"
          :multiple="false"
          :show-file-list="false"
          accept="application/pdf"
          @change="handleFileChange"
        >
          <div class="upload-zone">
            <div class="upload-inner">
              <div class="upload-icon">
                <NIcon size="30">
                  <CloudUpload />
                </NIcon>
              </div>
              <div v-if="!file">
                <h2 class="subhead">放入一份 PDF</h2>
                <p class="section-kicker">拖拽到这里，或点击选择文件。</p>
              </div>
              <div v-else class="file-chip">
                <NIcon color="#0f9f8f" size="20">
                  <DocumentAttach />
                </NIcon>
                <strong>{{ file.name }}</strong>
                <span>{{ formatSize(file.size) }}</span>
              </div>
              <NButton type="primary" secondary>
                {{ file ? "重新选择" : "选择 PDF" }}
              </NButton>
            </div>
          </div>
        </NUpload>

        <div class="config-grid">
          <div>
            <label class="field-label">处理策略</label>
            <NRadioGroup v-model:value="strategy" name="strategy" class="segmented-wide">
              <NRadioButton
                v-for="item in strategyOptions"
                :key="item.value"
                :value="item.value"
                :label="item.label"
              />
            </NRadioGroup>
            <p class="microcopy">
              {{ strategy === "auto" ? "由文档体检结果决定最佳引擎。" : "只使用你指定的首选引擎。" }}
            </p>
          </div>
          <div>
            <label class="field-label">首选引擎</label>
            <NSelect
              v-model:value="preferredEngine"
              :options="engineOptions"
              filterable
              placeholder="自动选择"
            />
            <p class="microcopy">固定引擎适合复测同一类文档。</p>
          </div>
        </div>

        <div class="action-bar">
          <div>
            <strong>输出格式</strong>
            <p class="microcopy">结构化 Markdown，可直接下载。</p>
          </div>
          <NButton
            type="primary"
            size="large"
            :disabled="!file"
            :loading="uploading"
            @click="submit"
          >
            <template #icon>
              <NIcon>
                <Rocket v-if="!uploading" />
                <Flash v-else />
              </NIcon>
            </template>
            {{ uploading ? `上传中 ${uploadProgress}%` : "开始转换" }}
          </NButton>
        </div>

        <NProgress
          v-if="uploading"
          :percentage="uploadProgress"
          :height="8"
          processing
          style="margin-top: 14px"
        />
      </section>

      <aside class="stack-column">
        <section class="panel panel-pad">
          <div class="panel-title-row">
            <div>
              <h2 class="subhead">六层处理流水线</h2>
              <p class="section-kicker">每一步都会在结果页实时回传。</p>
            </div>
            <NTag type="success" :bordered="false">Live</NTag>
          </div>

          <div class="pipeline-list">
            <div v-for="(layer, index) in pipelineLayers" :key="layer.title" class="pipeline-row">
              <div class="engine-index">{{ index + 1 }}</div>
              <NIcon size="20" color="#335cff">
                <component :is="layer.icon" />
              </NIcon>
              <div>
                <strong>{{ layer.title }}</strong>
                <p>{{ layer.text }}</p>
              </div>
            </div>
          </div>
        </section>

        <section class="panel panel-pad">
          <div class="panel-title-row">
            <div>
              <h2 class="subhead">七大 OCR 引擎</h2>
              <p class="section-kicker">按文档类型参与路由，不需要手工排队。</p>
            </div>
            <NTag type="info" :bordered="false">{{ availableCount }}/{{ store.engines.length }} 就绪</NTag>
          </div>

          <div class="engine-stack">
            <div v-for="engine in visibleEngines" :key="engine.id" class="engine-row">
              <div class="engine-index">{{ engine.index }}</div>
              <div>
                <div class="engine-name">{{ engine.name }}</div>
                <div class="engine-meta">{{ engine.note }}</div>
              </div>
              <span class="engine-state" :class="{ warn: !engine.available }">
                {{ engine.available ? "可用" : "未就绪" }}
              </span>
            </div>
          </div>

          <div class="metric-strip">
            <div class="metric">
              <div class="metric-value">{{ availableCount }}</div>
              <div class="metric-label">可用引擎</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ store.providers.length }}</div>
              <div class="metric-label">API Provider</div>
            </div>
            <div class="metric">
              <div class="metric-value">MD</div>
              <div class="metric-label">输出格式</div>
            </div>
          </div>
        </section>

        <section class="panel panel-pad api-nudge">
          <NIcon size="22" color="#0f9f8f">
            <Server />
          </NIcon>
          <div>
            <strong>API 校正层</strong>
            <p class="section-kicker">
              {{ providerReady ? "已启用 LLM Provider，结果页会展示校正过程。" : "未配置时仍可完成 OCR；配置后可增强表格、公式和阅读顺序修复。" }}
            </p>
          </div>
          <router-link to="/providers" class="nav-link">
            <NButton size="small" secondary type="primary">设置</NButton>
          </router-link>
        </section>
      </aside>
    </div>
  </div>
</template>
