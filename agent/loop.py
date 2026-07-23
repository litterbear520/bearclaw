import asyncio

from pathlib import Path

from bus.events import OutboundMessage
from bus.queue import MessageBus
from session.manager import Session, SessionManager
from memory.store import MemoryStore, Consolidator
from memory.dream import Dream
from agent.runner import AgentRunner, AgentRunSpec
from providers.base import LLMProvider
from tools.registry import ToolRegistry
from agent.context import ContextBuilder


class AgentLoop:

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        tools: ToolRegistry,
        workspace: Path,
    ):
        self.bus = bus
        self.provider = provider
        self.tools = tools
        self.workspace = workspace
        self._running = False

        self.sessions = SessionManager(workspace)
        self.store = MemoryStore(workspace)
        self.runner = AgentRunner()
        self.context = ContextBuilder(workspace)
        self.consolidator = Consolidator(
            self.store,
            self.sessions,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_schema,
        )
        self.dream = Dream(self.store, provider)

    def _save_turn(self, session: Session, messages: list[dict], skip: int) -> None:
        from datetime import datetime
        
        for m in messages[skip:]:
            entry = dict(m)
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
        
    async def run(self) -> None:
        self._running = True
        print("[AgentLoop] 启动")

        while self._running:
            # 消费入栈消息
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                session = self.sessions.get_or_create(msg.session_key) # 获取当前对话
                io_loop = asyncio.get_event_loop()

                await io_loop.run_in_executor(None, lambda: self.consolidator.maybe_consolidate(
                    session, self.provider, context_window=2000, max_tokens=200,
                ))

                messages = self.context.build_messages(
                    history=session.get_history(),
                    current_message=msg.content,
                    session_summary=session.metadata.get("_last_summary"),
                )

                session.messages.append({
                    "role": "user",
                    "content": msg.content,
                })

                spec = AgentRunSpec(
                    initial_messages=messages,
                    tools=self.tools,
                    provider=self.provider,
                )
                result = await io_loop.run_in_executor(None, lambda: self.runner.run(spec))
                self._save_turn(session, result.messages, len(messages))
                self.sessions.save(session)
                await io_loop.run_in_executor(None, self.dream.run)

                response = result.final_content or ""

            except Exception as e:
                print(f"[AgentLoop] 错误: {e}")
                response = f"处理出错: {e}"

            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=response,
            ))