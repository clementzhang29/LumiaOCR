"""
LLM 路由与 API Key 管理。
LLMRouter 负责注册 Provider 并按场景路由调用;
APIKeyManager 负责安全存储 API Key 信息 (内存中,不落盘明文)。
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from .base import LLMConfig
from .providers.auto_recognize import AutoRecognizeProvider

logger = logging.getLogger(__name__)


@dataclass
class APIKeyEntry:
    name: str
    provider: str = ""
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    extra: dict = field(default_factory=dict)


class APIKeyManager:
    """内存中的 API Key 注册表。重启后清空。"""

    def __init__(self):
        self._keys: dict[str, APIKeyEntry] = {}

    def add_key(self, entry: APIKeyEntry) -> None:
        self._keys[entry.name] = entry
        logger.info("APIKeyManager: registered %s", entry.name)

    def remove_key(self, name: str) -> bool:
        return self._keys.pop(name, None) is not None

    def get_key(self, name: str) -> Optional[APIKeyEntry]:
        return self._keys.get(name)

    def list_keys(self) -> list[dict]:
        return [
            {
                "name": k.name,
                "provider": k.provider,
                "base_url": k.base_url,
                "model": k.model,
                "api_key_masked": _mask_key(k.api_key),
            }
            for k in self._keys.values()
        ]


def _mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:3]}***{api_key[-4:]}"


class LLMRouter:
    """
    智能 LLM 路由：
      - register(name, base_url, api_key, model) 注册 Provider
      - route(scenario, messages) 按场景选择 Provider
      - verify_all() 并发验证所有 Provider
    """

    def __init__(self):
        self._providers: dict[str, "AutoRecognizeProvider"] = {}
        self._configs: dict[str, LLMConfig] = {}
        # scenario -> provider name
        self._scenario_map: dict[str, str] = {
            "ocr_correction": "default",
            "table_fix": "default",
            "formula_fix": "default",
            "ordering_fix": "default",
        }

    def register(self, name: str, base_url: str, api_key: str, model: str = "") -> "AutoRecognizeProvider":
        provider = AutoRecognizeProvider.create(base_url, api_key, model)
        self._providers[name] = provider
        self._configs[name] = provider.config
        # 第一个注册的 Provider 自动绑到 default 场景
        if "default" not in self._providers:
            self._providers["default"] = provider
            self._configs["default"] = provider.config
        logger.info("LLMRouter: registered provider %s (%s)", name, provider.config.provider)
        return provider

    def remove(self, name: str) -> bool:
        removed = self._providers.pop(name, None) is not None
        self._configs.pop(name, None)
        return removed

    def list_providers(self) -> list[dict]:
        return [
            {
                "name": n,
                "provider": c.provider,
                "model": c.model,
                "base_url": c.base_url,
            }
            for n, c in self._configs.items()
            if n != "default"
        ]

    def get(self, name: str) -> Optional["AutoRecognizeProvider"]:
        return self._providers.get(name)

    async def route(self, scenario: str, messages: list[dict], **kwargs) -> str:
        """按场景路由，返回 LLM 响应文本。"""
        name = self._scenario_map.get(scenario, "default")
        provider = self._providers.get(name)
        if provider is None:
            raise RuntimeError(f"No LLM provider available for scenario '{scenario}'")
        resp = await provider.chat(messages, **kwargs)
        if not resp.success:
            raise RuntimeError(f"LLM error: {resp.error}")
        return resp.content

    async def verify_all(self) -> dict:
        results: dict[str, bool] = {}
        tasks = []
        names = [n for n in self._providers.keys() if n != "default"]
        for name in names:
            tasks.append((name, self._providers[name].verify_connection()))
        coros = [t[1] for t in tasks]
        if coros:
            outcomes = await asyncio.gather(*coros, return_exceptions=True)
            for (name, _), outcome in zip(tasks, outcomes):
                if isinstance(outcome, Exception):
                    results[name] = False
                else:
                    results[name] = bool(outcome)
        return results
