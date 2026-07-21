"""
流程：
- 组装prompt
- 受限工具集合的agent循环
- LLM使用工具编辑记忆文件
- 成功后推进dream curosr
"""
from agent.runner import AgentRunner, AgentRunSpec
from memory.store import MemoryStore
from providers.base import LLMProvider
from session.manager import Session


class Dream:
    def __init__(self, store: MemoryStore, provider: LLMProvider):
        self.store = store
        self.provider = provider
        self.runner = AgentRunner()

    def run(self) -> str | None:
        result = self.store.build_dream_prompt()
        if result is None:
            print("[Dream] 没有新的历史纪录需要处理")
            return None

        prompt, last_cursor = result
        tools = self.store.build_dream_tools()
        session = Session(key="dream")

        spec = AgentRunSpec(system=prompt, tools=tools, provider=self.provider)
        self.runner.run(spec, session)

        self.store.set_last_dream_cursor(last_cursor)
        print(f"[Dream] 完成， cursor 推进到 {last_cursor}")
        return "ok"