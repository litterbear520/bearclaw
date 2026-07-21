import json

from datetime import datetime
from pathlib import Path
from typing import Any

from utils.prompt_templates import render_template


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
        tools.register(ReadFileTool())
        tools.register(EditFileTool())
        tools.register(WriteFileTool())
        return tools
