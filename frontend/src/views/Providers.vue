<script setup>
import { computed, onMounted, ref } from "vue"
import { useDialog, useMessage } from "naive-ui"
import {
  NAlert,
  NButton,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NSpace,
  NTag,
} from "naive-ui"
import {
  Add,
  CheckmarkCircle,
  Eye,
  EyeOff,
  Key,
  Link,
  LockClosed,
  Refresh,
  Save,
  Trash,
  Warning,
} from "@vicons/ionicons5"
import api from "../api"
import { useAppStore } from "../stores/app"

const store = useAppStore()
const message = useMessage()
const dialog = useDialog()

const providers = ref([])
const loading = ref(false)
const verifying = ref(false)
const showKey = ref(false)
const recognized = ref(null)
const testResults = ref(null)
const form = ref({ name: "", base_url: "", api_key: "", model: "" })

const providerTemplates = [
  { label: "OpenAI", slug: "openai", base: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  { label: "DeepSeek", slug: "deepseek", base: "https://api.deepseek.com", model: "deepseek-chat" },
  { label: "智谱 GLM", slug: "glm", base: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
  { label: "月之暗面 Kimi", slug: "kimi", base: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
  { label: "通义千问 Qwen", slug: "qwen", base: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
  { label: "Anthropic Claude", slug: "claude", base: "https://api.anthropic.com", model: "claude-sonnet-4-20250514" },
]

const knownProviders = [
  { pattern: "openai.com", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini"] },
  { pattern: "deepseek.com", name: "DeepSeek", models: ["deepseek-chat", "deepseek-reasoner"] },
  { pattern: "bigmodel.cn", name: "智谱 GLM", models: ["glm-4-plus", "glm-4-flash"] },
  { pattern: "moonshot.cn", name: "月之暗面 Kimi", models: ["moonshot-v1-8k", "moonshot-v1-32k"] },
  { pattern: "dashscope.aliyuncs.com", name: "通义千问 Qwen", models: ["qwen-plus", "qwen-max"] },
  { pattern: "anthropic.com", name: "Anthropic Claude", models: ["claude-sonnet-4-20250514", "claude-3-5-haiku"] },
]

const readyCount = computed(() => providers.value.length)

async function load() {
  const { data } = await api.providers.list()
  const keyMap = new Map((data.keys || []).map((item) => [item.name, item]))
  providers.value = (data.providers || []).map((provider) => ({
    ...provider,
    api_key_masked: keyMap.get(provider.name)?.api_key_masked || "",
  }))
}

function useTemplate(template) {
  form.value.base_url = template.base
  form.value.model = template.model
  if (!form.value.name) form.value.name = template.slug
  recognizeProvider()
}

function recognizeProvider() {
  const url = form.value.base_url.toLowerCase()
  const match = knownProviders.find((item) => url.includes(item.pattern))
  recognized.value = match || (url ? { name: "OpenAI 兼容接口", models: [] } : null)
  if (match && !form.value.model) form.value.model = match.models[0]
}

function resetForm() {
  form.value = { name: "", base_url: "", api_key: "", model: "" }
  recognized.value = null
  showKey.value = false
}

async function addProvider() {
  if (!form.value.name || !form.value.base_url || !form.value.api_key) {
    message.warning("请填写名称、API 地址和 Key")
    return
  }

  loading.value = true
  try {
    await api.providers.register(form.value)
    message.success("Provider 已保存，OCR 校正层可以使用")
    resetForm()
    await load()
    await store.fetchProviders()
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || "保存失败")
  } finally {
    loading.value = false
  }
}

function confirmRemove(name) {
  dialog.warning({
    title: "删除 Provider",
    content: `确定删除 ${name} 吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await api.providers.delete(name)
      message.success("已删除")
      await load()
      await store.fetchProviders()
    },
  })
}

async function verifyAll() {
  if (!providers.value.length) {
    message.info("还没有 Provider 可验证")
    return
  }

  verifying.value = true
  try {
    const { data } = await api.providers.verify()
    testResults.value = data.results || {}
    const ok = Object.values(testResults.value).filter(Boolean).length
    message.success(`连接检查完成：${ok}/${Object.keys(testResults.value).length} 成功`)
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || "验证失败")
  } finally {
    verifying.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="rise-in">
    <div class="hero-line">
      <div>
        <h1 class="section-title">API 设置</h1>
        <p class="section-kicker">配置 OpenAI 兼容 Provider 后，OCR 结果会进入表格、公式与阅读顺序校正层。</p>
      </div>
      <div class="status-pill" :class="{ muted: readyCount === 0 }">
        <span class="dot"></span>
        {{ readyCount ? `${readyCount} 个 Provider 已接入` : "暂未接入 Provider" }}
      </div>
    </div>

    <div class="provider-grid">
      <section class="panel panel-pad">
        <div class="panel-title-row">
          <div>
            <h2 class="subhead">新增 Provider</h2>
            <p class="section-kicker">Key 只保存在当前服务进程内，重启后需要重新配置。</p>
          </div>
          <NIcon size="24" color="#335cff"><Key /></NIcon>
        </div>

        <div class="template-grid">
          <button
            v-for="template in providerTemplates"
            :key="template.slug"
            class="template-card"
            type="button"
            @click="useTemplate(template)"
          >
            <strong>{{ template.label }}</strong>
            <span>{{ template.model }}</span>
          </button>
        </div>

        <NForm label-placement="top" class="provider-form">
          <NFormItem label="名称">
            <NInput v-model:value="form.name" placeholder="例如：my-openai">
              <template #prefix>
                <NIcon><Add /></NIcon>
              </template>
            </NInput>
          </NFormItem>
          <NFormItem label="API 地址">
            <NInput v-model:value="form.base_url" placeholder="https://api.openai.com/v1" @input="recognizeProvider">
              <template #prefix>
                <NIcon><Link /></NIcon>
              </template>
            </NInput>
          </NFormItem>
          <NFormItem label="API Key">
            <NInput v-model:value="form.api_key" :type="showKey ? 'text' : 'password'" placeholder="sk-...">
              <template #prefix>
                <NIcon><LockClosed /></NIcon>
              </template>
              <template #suffix>
                <NIcon class="icon-click" @click="showKey = !showKey">
                  <Eye v-if="showKey" />
                  <EyeOff v-else />
                </NIcon>
              </template>
            </NInput>
          </NFormItem>
          <NFormItem label="模型">
            <NInput v-model:value="form.model" :placeholder="recognized?.models?.[0] || 'gpt-4o-mini'" />
          </NFormItem>
        </NForm>

        <div class="form-footer">
          <NTag v-if="recognized" type="success" :bordered="false">
            已识别：{{ recognized.name }}
          </NTag>
          <span v-else class="microcopy">选择厂商或粘贴兼容 API 地址。</span>
          <NSpace>
            <NButton secondary @click="resetForm">清空</NButton>
            <NButton type="primary" :loading="loading" @click="addProvider">
              <template #icon>
                <NIcon><Save /></NIcon>
              </template>
              保存
            </NButton>
          </NSpace>
        </div>
      </section>

      <aside class="stack-column">
        <section class="panel panel-pad">
          <div class="panel-title-row">
            <div>
              <h2 class="subhead">Provider 状态</h2>
              <p class="section-kicker">保存后会自动参与 OCR 校正路由。</p>
            </div>
            <NButton secondary :loading="verifying" :disabled="providers.length === 0" @click="verifyAll">
              <template #icon>
                <NIcon><Refresh /></NIcon>
              </template>
              检查连接
            </NButton>
          </div>

          <NAlert v-if="testResults" type="info" :bordered="false" style="margin-bottom: 14px">
            <div class="verify-list">
              <span v-for="(ok, name) in testResults" :key="name">
                <NTag :type="ok ? 'success' : 'error'" size="small" :bordered="false">
                  {{ ok ? "通过" : "失败" }}
                </NTag>
                {{ name }}
              </span>
            </div>
          </NAlert>

          <NEmpty v-if="providers.length === 0" description="还没有 API Provider" />

          <div v-else class="provider-list">
            <div v-for="provider in providers" :key="provider.name" class="provider-row">
              <div>
                <div class="provider-title">
                  <strong>{{ provider.name }}</strong>
                  <NTag size="small" type="info" :bordered="false">{{ provider.provider }}</NTag>
                </div>
                <p>{{ provider.model || "默认模型" }}</p>
                <span>{{ provider.base_url }}</span>
                <small v-if="provider.api_key_masked">Key {{ provider.api_key_masked }}</small>
              </div>
              <NButton quaternary type="error" @click="confirmRemove(provider.name)">
                <template #icon>
                  <NIcon><Trash /></NIcon>
                </template>
              </NButton>
            </div>
          </div>
        </section>

        <section class="panel panel-pad api-health">
          <NIcon size="24" :color="readyCount ? '#0f9f8f' : '#b7791f'">
            <CheckmarkCircle v-if="readyCount" />
            <Warning v-else />
          </NIcon>
          <div>
            <strong>{{ readyCount ? "校正层已准备好" : "基础 OCR 仍可使用" }}</strong>
            <p class="section-kicker">
              {{ readyCount ? "上传新文档时，系统会把 Provider 注入表格、公式与阅读顺序修正流程。" : "没有 API 时会跳过 LLM 校正，仍然可以使用本地 OCR 引擎。" }}
            </p>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>
