<script setup>
import { computed, onMounted } from "vue"
import { useRoute } from "vue-router"
import { useAppStore } from "./stores/app"
import {
  NBadge,
  NButton,
  NConfigProvider,
  NDialogProvider,
  NIcon,
  NMessageProvider,
} from "naive-ui"
import { Chatbubbles, CloudDone, DocumentText, Settings } from "@vicons/ionicons5"

const store = useAppStore()
const route = useRoute()

const providerCount = computed(() => store.providers.length)

const themeOverrides = {
  common: {
    primaryColor: "#335cff",
    primaryColorHover: "#254ce6",
    primaryColorPressed: "#1e3fbf",
    primaryColorSuppl: "#0f9f8f",
    borderRadius: "8px",
    borderRadiusSmall: "6px",
    fontFamily:
      'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif',
  },
  Button: {
    borderRadiusMedium: "8px",
    borderRadiusLarge: "8px",
  },
  Card: {
    borderRadius: "8px",
  },
}

onMounted(() => {
  store.fetchEngines()
  store.fetchProviders()
})
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <div class="app-shell">
          <header class="topbar">
            <div class="topbar-inner">
              <router-link to="/rag" class="brand nav-link" aria-label="OCR Agent">
                <span class="brand-mark">
                  <NIcon size="20"><DocumentText /></NIcon>
                </span>
                <span>OCR Agent</span>
              </router-link>

              <nav class="topnav">
                <router-link to="/" class="nav-link">
                  <NButton :type="route.path === '/' || route.path === '/rag' ? 'primary' : 'default'" secondary>
                    <template #icon>
                      <NIcon><Chatbubbles /></NIcon>
                    </template>
                    OCR 智能体
                  </NButton>
                </router-link>
                <router-link to="/convert" class="nav-link">
                  <NButton :type="route.path === '/convert' ? 'primary' : 'default'" secondary>
                    <template #icon>
                      <NIcon><DocumentText /></NIcon>
                    </template>
                    单文档转换
                  </NButton>
                </router-link>
                <router-link to="/providers" class="nav-link">
                  <NBadge :value="providerCount" :show="providerCount > 0" :max="99">
                    <NButton :type="route.path === '/providers' ? 'primary' : 'default'" secondary>
                      <template #icon>
                        <NIcon><Settings /></NIcon>
                      </template>
                      模型 API
                    </NButton>
                  </NBadge>
                </router-link>
              </nav>

              <div class="topbar-spacer"></div>

              <div class="status-pill">
                <span class="dot"></span>
                <NIcon size="16"><CloudDone /></NIcon>
                OCR 后可直接问答
              </div>
            </div>
          </header>

          <main class="page-container">
            <router-view />
          </main>
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
