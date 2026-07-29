from __future__ import annotations

from dataclasses import dataclass
from providers.base import GenerationSettings, LLMProvider


@dataclass(frozen=True, slots=True)
class LLMRuntime:
    provider: LLMProvider
    model: str
    generation: GenerationSettings
    context_window_tokens: int

    @classmethod
    def capture(
        cls,
        provider: LLMProvider,
        model: str,
        *,
        context_window_tokens: int,
    ) -> LLMRuntime:
        defaults = GenerationSettings()
        generation = getattr(provider, "generation", defaults)
        return cls(
            provider=provider,
            model=model,
            generation=GenerationSettings(
                temperature=getattr(generation, "temperature", defaults.temperature),
                max_tokens=getattr(generation, "max_tokens", defaults.max_tokens),
                reasoning_effort=getattr(generation, "reasoning_effort", defaults.reasoning_effort),
            ),
            context_window_tokens=context_window_tokens,
        )
