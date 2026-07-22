import asyncio

from pathlib import Path

from bus.events import OutboundMessage
from bus.queue import MessageBus
from session.manager import SessionManager
from session.consolidator import Consolidator
from memory.store import MemoryStore
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
        self.consolidator = Consolidator(self.store, self.sessions)
        self.dream = Dream(self.store, provider)
        self.runner = AgentRunner()
        self.context = ContextBuilder(workspace)

    async def run(self) -> None:
        self._running = True
        print("[AgentLoop] 启动")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                session = self.sessions.get_or_create(msg.session_key)
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
                await io_loop.run_in_executor(None, lambda: self.runner.run(spec, session))
                self.sessions.save(session)
                await io_loop.run_in_executor(None, self.dream.run)

                response = ""
                for m in reversed(session.messages):
                    if m.get("role") == "assistant" and m.get("content"):
                        response = m["content"]
                        break
            except Exception as e:
                print(f"[AgentLoop] 错误: {e}")
                response = f"处理出错: {e}"

            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=response,
            ))