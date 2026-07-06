import { createRouter, createWebHistory } from "vue-router"
import Home from "./views/Home.vue"
import Providers from "./views/Providers.vue"
import Result from "./views/Result.vue"
import Rag from "./views/Rag.vue"

const routes = [
  { path: "/", name: "AgentHome", component: Rag },
  { path: "/convert", name: "Home", component: Home },
  { path: "/providers", name: "Providers", component: Providers },
  { path: "/rag", name: "RAG", component: Rag },
  { path: "/result/:id", name: "Result", component: Result, props: true },
]

export default createRouter({ history: createWebHistory(), routes })
