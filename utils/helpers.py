import json
import tiktoken

from pathlib import Path

from functools import lru_cache
from contextlib import suppress
from typing import Any

_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"
_TOOLS_TOKEN_CACHE_MAX_ENTRIES = 64
_TOOLS_TOKEN_CACHE: dict[int, tuple[tuple[int, ...], dict[bool, int]]] = {}


def _cache_tools_token_count(
    tools_id: int,
    fingerprint: tuple[int, ...],
    counts: dict[bool, int],
) -> None:
    if (tools_id not in _TOOLS_TOKEN_CACHE
        and len(_TOOLS_TOKEN_CACHE) >= _TOOLS_TOKEN_CACHE_MAX_ENTRIES):

        _TOOLS_TOKEN_CACHE.pop(next(iter(_TOOLS_TOKEN_CACHE)))
    _TOOLS_TOKEN_CACHE[tools_id] = (fingerprint, counts)


def _estimate_tools_tokens(
    enc: Any,
    tools: list[dict[str, Any]],
    *,
    leading_separator: bool,
) -> int:
    tools_id = id(tools)
    fingerprint = tuple(id(tool) for tool in tools)

    cached = _TOOLS_TOKEN_CACHE.get(tools_id)
    if cached and cached[0] == fingerprint:
        token_count = cached[1].get(leading_separator)
        if token_count is not None:
            return token_count
        counts = cached[1]
    else:
        counts = {}

    rendered = json.dumps(tools, ensure_ascii=False)
    if leading_separator:
        rendered = "\n" + rendered

    token_count = len(enc.encode(rendered))
    counts[leading_separator] = token_count
    _cache_tools_token_count(tools_id, fingerprint, counts)
    return token_count


@lru_cache(maxsize=1)
def _get_token_encoding() -> Any:
    return tiktoken.get_encoding("cl100k_base")


def estimate_message_tokens(message: dict) -> int:
    parts: list[str] = []

    content = message.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if text:
                    parts.append(text)
            else:
                parts.append(json.dumps(part, ensure_ascii=False))
    elif content is not None:
        parts.append(json.dumps(content, ensure_ascii=False))
    if message.get("tool_calls"):
        parts.append(json.dumps(message["tool_calls"], ensure_ascii=False))

    for key in ("name", "tool_call_id"):
        value = message.get(key)
        if isinstance(value, str) and value:
            parts.append(value)

    rc = message.get("reasoning_content")
    if isinstance(rc, str) and rc:
        parts.append(rc)

    payload = "\n".join(parts)
    if not payload:
        return 4

    enc = _get_token_encoding()
    return max(4, len(enc.encode(payload)) + 4)


def estimate_prompt_tokens(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> int:
    try:
        enc = _get_token_encoding()
        parts: list[str] = []

        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        txt = part.get("text", "")
                        if txt:
                            parts.append(txt)

            tc = msg.get("tool_calls")
            if tc:
                parts.append(json.dumps(tc, ensure_ascii=False))

            rc = msg.get("reasoning_content")
            if isinstance(rc, str) and rc:
                parts.append(rc)

            for key in ("name", "tool_call_id"):
                value = msg.get(key)
                if isinstance(value, str) and value:
                    parts.append(value)

        tool_tokens = (
            _estimate_tools_tokens(enc, tools, leading_separator=bool(parts))
            if tools else 0
        )

        per_message_overhead = len(messages) * 4
        message_tokens = len(enc.encode("\n".join(parts))) if parts else 0

        return message_tokens + tool_tokens + per_message_overhead
    except Exception:
        return 0


def estimate_prompt_tokens_chain(
    provider: Any,
    model: str | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> tuple[int, str]:
    provider_counter = getattr(provider, "estimate_prompt_tokens", None)

    if callable(provider_counter):
        with suppress(Exception):
            tokens, source = provider_counter(messages, tools, model)
            if isinstance(tokens, (int, float)) and tokens > 0:
                return int(tokens), str(source or "provider_counter")
    estimated = estimate_prompt_tokens(messages, tools)
    if estimated > 0:
        return int(estimated), "tiktoken"

    return 0, "none"
    

def sync_workspace_templates(workspace: Path) -> list[str]:
    added: list[str] = []


    def _write(src: Path, dest: Path) -> None:
        content = src.read_text(encoding="utf-8")
        if dest.exists():
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        added.append(str(dest.relative_to(workspace)))

    for name in ("AGENTS.md", "SOUL.md", "USER.md"):
        _write(_TEMPLATES_ROOT / name, workspace / name)

    return added


def find_legal_message_start(messages: list[dict[str, Any]]) -> int:
    declared: set[str] = set()
    start = 0
    for i, msg in enumerate(messages):
        role = msg.get("role")
        if role == "assistant":
            for tc in msg.get("tool_calls") or []:
                if isinstance(tc, dict) and tc.get("id"):
                    declared.add(str(tc["id"]))
        elif role == "tool":
            tid = msg.get("tool_call_id")
            if tid and str(tid) not in declared:
                start = i + 1
                declared.clear()
    return start