import json
import os

from typing import Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class RetentionResult:
    dropped: list[dict]
    already_consolidated_count: int


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


    def retain_recent_legal_suffix(
        self,
        max_messages: int,
        *,
        extend_to_user: bool = False,
    ) -> RetentionResult:
        if max_messages <= 0:
            dropped = list(self.messages)
            lc = self.last_consolidated
            self.clear()
            return RetentionResult(
                dropped=dropped,
                already_consolidated_count=min(lc, len(dropped)),
            )
        if len(self.messages) <= max_messages:
            return RetentionResult(
                dropped=[],
                already_consolidated_count=0,
            )

        original = list(self.messages)
        before_lc = self.last_consolidated

        start_idx = max(0, len(self.messages) - max_messages)
        if extend_to_user:
            start_idx = next(
                (i for i in range(start_idx, -1, -1) if self.messages[i].get("role") == "user"),
                start_idx,
            )
        retained = self.messages[start_idx:]
        first_user = next((i for i, m in enumerate(retained) if m.get("role") == "user"), None)
        if first_user is not None:
            retained = retained[first_user:]

        from utils.helpers import find_legal_message_start
        start = find_legal_message_start(retained)
        if start:
            retained = retained[start:]

        retained_ids = set(id(m) for m in retained)
        dropped = [m for m in original if id(m) not in retained_ids]

        already_consolidated = sum(
            1 for i, m in enumerate(original)
            if i < before_lc and id(m) not in retained_ids
        )
        
        new_lc = sum(
            1 for i, m in enumerate(original)
            if i < before_lc and id(m) in retained_ids
        )

        self.messages = retained
        self.last_consolidated = new_lc
        self.updated_at = datetime.now()
        return RetentionResult(
            dropped=dropped,
            already_consolidated_count=already_consolidated,
        )


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

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            fallback_time = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                            sessions.append({
                                "key": data.get("key") or path.stem,
                                "created_at": data.get("created_at") or fallback_time,
                                "updated_at": data.get("updated_at") or fallback_time,
                            })
            except FileNotFoundError:
                continue
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)