"""
LLM 抽象基类 — 所有 LLM Provider 的统一接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: Optional[dict] = None
    error: Optional[str] = None
    success: bool = True


class LLMError(Exception):
    def __init__(self, provider: str, model: str, message: str, status_code: int = 500):
        self.provider = provider
        self.model = model
        self.status_code = status_code
        super().__init__(f"[{provider}/{model}] {message}")


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    timeout: int = 120
    extra_headers: dict = field(default_factory=dict)


class BaseLLM(ABC):
    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict], **kwargs):
        ...

    async def structured_extract(self, prompt: str, text: str, schema: Optional[dict] = None) -> LLMResponse:
        system_msg = "You are a precise document extraction assistant."
        if schema:
            system_msg += f"\nOutput format: {schema}"
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"{prompt}\n\n{text}"},
        ]
        return await self.chat(messages)

    @abstractmethod
    async def verify_connection(self) -> bool:
        ...

    def _build_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        headers.update(self.config.extra_headers)
        return headers
