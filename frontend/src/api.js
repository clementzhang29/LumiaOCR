import axios from "axios"

const api = axios.create({ baseURL: "/api" })

export default {
  health: () => api.get("/health"),
  engines: () => api.get("/engines"),
  providers: {
    list: () => api.get("/providers"),
    register: (data) => api.post("/providers", data),
    delete: (name) => api.post(`/providers/delete/${name}`),
    verify: () => api.post("/providers/verify"),
  },
  rag: {
    status: () => api.get("/rag/status"),
    ingest: (file, onProgress) => {
      const form = new FormData()
      form.append("file", file)
      return api.post("/rag/ingest", form, {
        onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded / e.total) * 100)),
      })
    },
    query: (question, topK = 5) => api.post("/rag/query", { question, top_k: topK }),
  },
  agent: {
    documents: () => api.get("/agent/documents"),
    upload: (files, strategy, preferredEngine, onProgress) => {
      const form = new FormData()
      files.forEach((file) => form.append("files", file))
      form.append("strategy", strategy)
      form.append("preferred_engine", preferredEngine || "")
      return api.post("/agent/upload", form, {
        onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded / e.total) * 100)),
      })
    },
    action: (payload) => api.post("/agent/action", payload),
  },
  convert: (file, strategy, preferredEngine, onProgress) => {
    const form = new FormData()
    form.append("file", file)
    form.append("strategy", strategy)
    form.append("preferred_engine", preferredEngine)
    return api.post("/convert", form, {
      onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded / e.total) * 100)),
    })
  },
  status: (id) => api.get(`/status/${id}`),
  result: (id) => api.get(`/result/${id}`),
  download: (id) => `${api.defaults.baseURL}/download/${id}`,
}
