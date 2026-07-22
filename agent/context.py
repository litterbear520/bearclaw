from pathlib import Path
from typing import Any

from utils.prompt_templates import render_template


class ContextBuilder:
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md"]

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def build_system_prompt(
        self, 
        session_summary: str | None = None,
        workspace: Path | None = None,
        ) -> str:
        root = workspace or self.workspace
        parts = [self._get_identity(workspace=root)]

        bootstrap = self._load_bootstrap_files(root)
        if bootstrap:
            parts.append(bootstrap)

        if session_summary:
            parts.append(f"[Archived Context Summary]\n\n{session_summary}")

        return "\n\n---\n\n".join(parts)

    def _get_identity(self, workspace: Path | None = None) -> str:
        root = workspace or self.workspace

        return render_template(
            "identity.md",
            workspace=str(root),
        )

    def _load_bootstrap_files(self, workspace: Path | None = None) -> str:
        parts = []
        root = workspace or self.workspace

        for filename in self.BOOTSTRAP_FILES:
            file_path = root / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")

        return "\n\n".join(parts) if parts else ""

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        session_summary: str | None = None,
    ) -> list[dict[str, Any]]:

        messages = [
            {
                "role": "system",
                "content": self.build_system_prompt(session_summary=session_summary),
            },
            *history,
        ]
        messages.append({
            "role": "user",
            "content": current_message,
        })
        return messages