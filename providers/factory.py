import os

from providers.base import LLMProvider


def make_provider() -> LLMProvider:
    api_key = os.getenv("LLM_API_KEY") or None
    base_url = os.getenv("LLM_BASE_URL") or None
    model = os.getenv("LLM_MODEL") or None
    backend = os.getenv("LLM_BACKEND", "openai_compat")

    if backend == "anthropic":
        from providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            base_url=base_url,
            default_model=model or "claude-sonnet-4-20250514",
        )
    else:
        from providers.openai_compat_provider import OpenAICompatProvider

        return OpenAICompatProvider(
            api_key=api_key,
            base_url=base_url,
            default_model=model or "deepseek-v4-flash",
        )