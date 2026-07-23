import json
import os

from typing import Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Session:
    key: str
    last_consolidated: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()

    def get_history(self) -> list[dict[str, Any]]:
        return self.messages[self.last_consolidated:]

    def clear(self) -> None:
        self.messages = []
        self.updated_at = datetime.now()

    def estimate_tokens(self) -> int:
        from utils.helpers import estimate_message_tokens
        return sum(estimate_message_tokens(msg) for msg in self.messages[self.last_consolidated:])


class SessionManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = workspace / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, key: str) -> Path:
        return self.sessions_dir / f"{key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        session = self._load(key)
        if session is None:
            session = Session(key=key)
        return session
    
    def _load(self, key:str) -> Session | None:
        path = self._get_session_path(key)
        if not path.exists():
            return None

        messages = []
        metadata = {}
        last_consolidated = 0
        created_at = None
        updated_at = None

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("_type") == "metadata":
                    metadata = data.get("metadata", {})
                    last_consolidated = data.get("last_consolidated", 0)
                    created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                    updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
                else:
                    messages.append(data)

        return Session(
            key=key,
            messages=messages,
            last_consolidated=last_consolidated,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            metadata=metadata,
        )
        
    def save(self, session: Session) -> None:
        path = self._get_session_path(session.key)
        tmp_path = path.with_suffix(".jsonl.tmp")

        with open(tmp_path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "last_consolidated": session.last_consolidated,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)