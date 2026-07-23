import json
import tiktoken

from pathlib import Path


_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"

def _get_encoding():
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

    if message.get("tool_calls"):
        parts.append(json.dumps(message["tool_calls"], ensure_ascii=False))

    for key in ("name", "tool_call_id"):
        value = message.get(key)
        if isinstance(value, str) and value:
            parts.append(value)

    payload = "\n".join(parts)
    if not payload:
        return 4

    enc = _get_encoding()
    return max(4, len(enc.encode(payload)) + 4)


def estimate_prompt_tokens(
    messages: list[dict],
    tools: list[dict] | None = None,
) -> int:
    total = sum(estimate_message_tokens(m) for m in messages)
    if tools:
        total += len(_get_encoding().encode(json.dumps(tools, ensure_ascii=False)))
    return total

    
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