from dataclasses import dataclass

from providers.base import LLMProvider
from tools.registry import ToolRegistry
from session.manager import Session

@dataclass
class AgentRunSpec:
    system: str
    tools: ToolRegistry
    provider: LLMProvider
    max_iterations: int = 50


class AgentRunner:

    def run(self, spec: AgentRunSpec, session: Session) -> None:
        for iteration in range(spec.max_iterations):
            response = spec.provider.chat(
                tools=spec.tools.get_schema(),
                messages=[{"role": "system", "content": spec.system}] + session.get_history(),
                max_tokens=10000,
            )
            ai_msg = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                ai_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.args}}
                    for tc in response.tool_calls
                ]
            session.messages.append(ai_msg)

            if response.finish_reason != "tool_calls":
                return

            for tc in response.tool_calls:
                print(f"使用工具：{tc.name}, 参数：{tc.args}")
                output = spec.tools.run(tc.name, **(tc.args if isinstance(tc.args, dict) else {}))
                print(f"工具结果：{output}")
                session.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output,
                })