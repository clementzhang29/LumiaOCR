"""
OpenAI 兼容接口 Provider — 支持 OpenAI / DeepSeek / GLM / Kimi / Qwen 等。
"""
import httpx
from ..base import BaseLLM, LLMConfig, LLMResponse, LLMError


class OpenAICompatProvider(BaseLLM):
    """
    通用 OpenAI 兼容接口适配器。
    支持的 API:
      - OpenAI:     https://api.openai.com/v1
      - DeepSeek:   https://api.deepseek.com/v1
      - GLM (智谱): https://open.bigmodel.cn/api/paas/v4
      - Kimi (月之暗面): https://api.moonshot.cn/v1
      - Qwen (通义千问): https://dashscope.aliyuncs.com/compatible-mode/v1
      - 任何其他 OpenAI 兼容接口
    """

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise LLMError(
                        self.config.provider, self.config.model,
                        f"HTTP {resp.status_code}: {resp.text}",
                        resp.status_code,
                    )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage")
                return LLMResponse(
                    content=content,
                    model=data.get("model", self.config.model),
                    provider=self.config.provider,
                    usage=usage,
                )
        except httpx.TimeoutException as e:
            raise LLMError(self.config.provider, self.config.model, f"Timeout: {e}")
        except Exception as e:
            raise LLMError(self.config.provider, self.config.model, str(e))

    async def chat_stream(self, messages: list[dict], **kwargs):
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }
        headers = self._build_headers()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    raise LLMError(
                        self.config.provider, self.config.model,
                        f"HTTP {resp.status_code}: {error_body.decode()}",
                        resp.status_code,
                    )
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]

    async def verify_connection(self) -> bool:
        try:
            resp = await self.chat([
                {"role": "user", "content": "Hello, respond with just 'OK'."}
            ])
            return resp.success
        except Exception:
            return False
