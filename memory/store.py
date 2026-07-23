import json

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from utils.prompt_templates import render_template
from session.manager import Session, SessionManager


class MemoryStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.memory_dir / "history.jsonl"
        self._cursor_file = self.memory_dir / ".cursor"

    def _next_cursor(self) -> int:
        if self._cursor_file.exists():
            try:
                return int(self._cursor_file.read_text(encoding="utf-8").strip()) + 1
            except (ValueError, OSError):
                pass
        entries = self._read_entries()
        if entries:
            return max(e.get("cursor", 0) for e in entries) + 1
        return 1

    def _read_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        if not self.history_file.exists():
            return entries
        with open(self.history_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def append_history(self, entry: str, *, session_key: str | None = None) -> int:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = entry.rstrip()
        cursor = self._next_cursor()
        record: dict[str, Any] = {"cursor": cursor, "timestamp": ts, "content": content}
        if session_key:
            record["session_key"] = session_key
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._cursor_file.write_text(str(cursor), encoding="utf-8")
        return cursor

    def read_unprocessed_history(self, since_cursor: int) -> list[dict[str, Any]]:
        return [e for e in self._read_entries() if e.get("cursor", 0) > since_cursor]

    def get_last_dream_cursor(self) -> int:
        dream_cursor_file = self.memory_dir / ".dream_cursor"
        if dream_cursor_file.exists():
            try:
                return int(dream_cursor_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pass
        return 0

    def set_last_dream_cursor(self, cursor: int) -> None:
        dream_cursor_file = self.memory_dir / ".dream_cursor"
        dream_cursor_file.write_text(str(cursor), encoding="utf-8")

    def _render_current_memory_files(self) -> str:
        files = [
            ("SOUL.md", self.workspace / "SOUL.md"),
            ("USER.md", self.workspace / "USER.md"),
            ("memory/MEMORY.md", self.memory_dir / "MEMORY.md"),
        ]
        blocks = []
        for label, path in files:
            try:
                content = path.read_text(encoding="utf-8") if path.exists() else ""
            except OSError:
                content = ""
            blocks.append(f"### {label}\n{content}" if content.strip() else f"### {label}\n(empty)")
        return "## Current Memory Files\n" + "\n\n".join(blocks)

    def build_dream_prompt(self, *, max_entries: int = 20) -> tuple[str, int] | None:
        last_cursor = self.get_last_dream_cursor()
        entries = self.read_unprocessed_history(since_cursor=last_cursor)
        if not entries:
            return None

        batch = entries[:max_entries]
        history_text = "\n".join(
            f"[{e['timestamp']}] {e['content']}"
            for e in batch
        )
        template = render_template("dream.md", strip=True)
        files_section = self._render_current_memory_files()
        prompt = (
            f"{template}\n\n{files_section}\n\n"
            f"## Conversation History\n{history_text}"
        )
        return (prompt, batch[-1]["cursor"])

    def build_dream_tools(self):
        from tools.registry import ToolRegistry
        from tools.filesystem import ReadFileTool, EditFileTool, WriteFileTool

        tools = ToolRegistry()
        tools.register(ReadFileTool(workspace=self.workspace))
        tools.register(EditFileTool(workspace=self.workspace))
        tools.register(WriteFileTool(workspace=self.workspace))
        return tools


class Consolidator:

    _SAFETY_BUFFER = 1024

    def __init__(
        self,
        store: MemoryStore,
        sessions: SessionManager,
        build_messages: Callable,
        get_tool_definitions: Callable,
        consolidation_ratio: float = 0.5,
    ) -> None:
        self.store = store
        self.sessions = sessions
        self._build_messages = build_messages
        self._get_tool_definitions = get_tool_definitions
        self.consolidation_ratio = consolidation_ratio

    def estimate_session_prompt_tokens(self, session: Session) -> int:
        from utils.helpers import estimate_prompt_tokens

        history = session.messages[session.last_consolidated:]
        summary = session.metadata.get("_last_summary")
        probe_messages = self._build_messages(
            history=history,
            current_message="[token-probe]",
            session_summary=summary,
        )
        return estimate_prompt_tokens(probe_messages, self._get_tool_definitions())

    def pick_consolidation_boundary(self, session: Session, tokens_to_remove: int) -> tuple[int, int] | None:
        from utils.helpers import estimate_message_tokens

        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_remove <= 0:
            return None

        removed_tokens = 0
        last_boundary: tuple[int, int] | None = None

        for idx in range(start, len(session.messages)):
            msg = session.messages[idx]
            if idx > start and msg.get("role") == "user":
                last_boundary = (idx, removed_tokens)
                if removed_tokens >= tokens_to_remove:
                    return last_boundary
            removed_tokens += estimate_message_tokens(msg)

        return last_boundary

    @staticmethod
    def _format_messages(messages: list[dict]) -> str:
        lines = []
        for msg in messages:
            if not msg.get("content"):
                continue
            role = msg["role"].upper()
            content = msg["content"]
            if not isinstance(content, str):
                content = str(content)
            ts = msg.get("timestamp", "")
            prefix = f"[{ts[:16]}] " if ts else ""
            lines.append(f"{prefix}{role}: {content}")
        return "\n".join(lines)

    def archive(self, messages: list[dict], provider, session_key: str | None = None) -> str | None:
        if not messages:
            return None

        formatted = self._format_messages(messages)
        try:
            response = provider.chat(
                messages=[
                    {"role": "system", "content": render_template("consolidator_archive.md", strip=True)},
                    {"role": "user", "content": formatted}
                ],
                tools=[],
                max_tokens=2000,
            )
            summary = response.content or "(nothing)"
            self.store.append_history(summary, session_key=session_key)
            return summary
        except Exception:
            return None

    def maybe_consolidate(
        self,
        session: Session,
        provider,
        context_window: int,
        max_tokens: int,
    ) -> str | None:
        budget = context_window - max_tokens - self._SAFETY_BUFFER
        if budget <= 0:
            return None

        estimated = self.estimate_session_prompt_tokens(session)
        print(f"[压缩检查] estimated={estimated} budget={budget}")
        if estimated < budget:
            return None

        target = int(budget * self.consolidation_ratio)
        summary = None

        for _ in range(5):
            if estimated <= target:
                break

            boundary = self.pick_consolidation_boundary(session, estimated - target)
            if boundary is None:
                print("[压缩] 找不到安全切割点，跳过")
                break

            end_idx = boundary[0]
            chunk = session.messages[session.last_consolidated:end_idx]
            if not chunk:
                break

            print(f"[压缩] 开始压缩: chunk={len(chunk)} msgs, estimated={estimated}, target={target}")
            summary = self.archive(chunk, provider, session_key=session.key)
            session.last_consolidated = end_idx
            self.sessions.save(session)

            if not summary:
                break

            estimated = self.estimate_session_prompt_tokens(session)

        if summary and summary != "(nothing)":
            session.metadata["_last_summary"] = summary
            self.sessions.save(session)

        return summary
