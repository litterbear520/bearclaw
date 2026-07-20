import json
import tiktoken


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