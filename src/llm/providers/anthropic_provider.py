import httpx
from ..base import BaseLLM, LLMConfig, LLMResponse, LLMError


class AnthropicProvider(BaseLLM):
    API_VERSION = "2023-06-01"

    def _build_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": self.API_VERSION,
        }

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        url = f"{self.config.base_url.rstrip('/')}/v1/messages"
        system = None
        anthro_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthro_msgs.append({"role": msg["role"], "content": msg["content"]})
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": anthro_msgs,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._build_headers())
                if resp.status_code != 200:
                    raise LLMError(self.config.provider, self.config.model, f"HTTP {resp.status_code}: {resp.text}", resp.status_code)
                data = resp.json()
                content = "".join(b["text"] for b in data.get("content", []) if b["type"] == "text")
                return LLMResponse(content=content, model=data.get("model", self.config.model), provider=self.config.provider)
        except Exception as e:
            raise LLMError(self.config.provider, self.config.model, str(e))

    async def chat_stream(self, messages: list[dict], **kwargs):
        ...

    async def verify_connection(self) -> bool:
        try:
            await self.chat([{"role": "user", "content": "OK"}])
            return True
        except Exception:
            return False