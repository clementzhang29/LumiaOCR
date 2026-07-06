from ..base import LLMConfig
from .openai_compat import OpenAICompatProvider
from .anthropic_provider import AnthropicProvider


KNOWN_PROVIDERS = {
    "openai": {"url_patterns": ["api.openai.com"], "type": "openai-compat", "note": "OpenAI"},
    "deepseek": {"url_patterns": ["api.deepseek.com"], "type": "openai-compat", "note": "DeepSeek"},
    "glm": {"url_patterns": ["open.bigmodel.cn"], "type": "openai-compat", "note": "智谱 GLM"},
    "kimi": {"url_patterns": ["api.moonshot.cn"], "type": "openai-compat", "note": "月之暗面 Kimi"},
    "qwen": {"url_patterns": ["dashscope.aliyuncs.com"], "type": "openai-compat", "note": "阿里通义千问"},
    "anthropic": {"url_patterns": ["api.anthropic.com"], "type": "anthropic", "note": "Anthropic Claude"},
}


class AutoRecognizeProvider:
    @staticmethod
    def create(base_url: str, api_key: str, model: str = ""):
        base_url = base_url.rstrip("/").lower()
        recognized = None
        for name, info in KNOWN_PROVIDERS.items():
            for pattern in info["url_patterns"]:
                if pattern in base_url:
                    recognized = name
                    break
            if recognized:
                break
        provider_type = "openai-compat"
        if recognized:
            provider_type = KNOWN_PROVIDERS[recognized]["type"]
        config = LLMConfig(
            provider=recognized or "custom",
            model=model or _get_default_model(recognized),
            api_key=api_key,
            base_url=base_url,
        )
        if provider_type == "anthropic":
            return AnthropicProvider(config)
        return OpenAICompatProvider(config)

    @staticmethod
    def recognize(base_url: str) -> dict:
        base_url = base_url.rstrip("/").lower()
        for name, info in KNOWN_PROVIDERS.items():
            for pattern in info["url_patterns"]:
                if pattern in base_url:
                    return {"provider": name, "type": info["type"], "note": info.get("note", "")}
        return {"provider": "custom", "type": "openai-compat", "note": "Unknown API, using OpenAI compatible mode"}


def _get_default_model(provider: str) -> str:
    return {
        "openai": "gpt-4o-mini", "deepseek": "deepseek-chat",
        "glm": "glm-4-flash", "kimi": "moonshot-v1-8k",
        "qwen": "qwen-plus", "anthropic": "claude-3-5-haiku-20241022",
    }.get(provider, "gpt-4o-mini")