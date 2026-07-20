from session.manager import Session, SessionManager


class Consolidator:
    def __init__(self, sessions: SessionManager, consolidation_ratio: float=0.5) -> None:
        self.sessions = sessions
        self.consolidation_ratio = consolidation_ratio
    
    def pick_consolidation_boundary(self, session: Session, tokens_to_romove: int) -> int | None:
        from utils.tokens import estimate_message_tokens

        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_romove <= 0:
            return None

        removed_tokens = 0
        last_boundary = None

        for idx in range(start, len(session.messages)):
            msg = session.messages[idx]
            if idx > start and msg.get("role") == "user":
                last_boundary = idx
                if removed_tokens >= tokens_to_romove:
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
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def archive(self, messages: list[dict], provider, session_key: str | None = None) -> str | None:
        if not messages:
            return None

        formatted = self._format_messages(messages)
        try:
            response = provider.chat(
                messages=[
                    {"role": "system", "content": "提炼这段对话的关键事实，每行简洁一条。如果没有值得记录的内容，输出：(nothing)"},
                    {"role": "user", "content": formatted}
                ],
                tools=[],
                max_tokens=2000,
            )
            return response.content or "(nothing)"
        except Exception:
            return None

    def maybe_consolidate(
        self,
        session: Session,
        provider,
        context_window: int,
        max_tokens: int
        ) -> str | None:
        budget = context_window - max_tokens - 1024
        if budget <= 0:
            return None

        estimated = session.estimate_tokens()
        print(f"[压缩检查] estimated={estimated} budget={budget}")
        if estimated < budget:
            return None

        target = int(budget * self.consolidation_ratio)

        for _ in range(5):
            if estimated <= target:
                break
                
            boundary = self.pick_consolidation_boundary(session, estimated - target)
            if boundary is None:
                break

            chunk = session.messages[session.last_consolidated:boundary]
            if not chunk:
                break

            summary = self.archive(chunk, provider, session_key=session.key)
            session.last_consolidated = boundary
            self.sessions.save(session)

            if not summary:
                break

            estimated = session.estimate_tokens()
                
        if summary and summary != "(nothing)":
            session.metadata["_last_summary"] = summary
            self.sessions.save(session)

        return summary