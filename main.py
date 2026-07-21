import os

from pathlib import Path
from dotenv import load_dotenv

from tools.loader import load_tools
from providers.factory import make_provider
from session.manager import SessionManager
from session.consolidator import Consolidator
from utils.prompt_templates import render_template


load_dotenv()

registry = load_tools()
provider = make_provider()

SYSTEM = render_template("identity.md", workspace=os.getcwd())


# 循环构建
def agent_loop(session, system):
    while True:
        response = provider.chat(
            tools=registry.get_schema(), 
            messages=[{"role": "system", "content": system}] + session.get_history(), 
            max_tokens=10000
        )
        
        ai_msg: dict = {"role": "assistant", "content": response.content}
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
            output = registry.run(tc.name, **(tc.args if isinstance(tc.args, dict) else {}))
            print(f"工具结果：{output}")
            session.messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output
            })

        
# 主函数
if __name__ == "__main__":
    print("Welcome to bearclaw!")
    sessions = SessionManager(Path.cwd())
    session = sessions.get_or_create("default")
    consolidator = Consolidator(sessions)

    while True: 
        try: 
            query = input(">> ")
        except Exception:
            break

        session.messages.append({"role": "user", "content": query})
        consolidator.maybe_consolidate(session, provider, context_window=2000, max_tokens=200)

        system = SYSTEM
        if session.metadata.get("_last_summary"):
            system += f"\n\n[Archived Context Summary]\n{session.metadata['_last_summary']}"
        agent_loop(session, system)
        sessions.save(session)
        for msg in reversed(session.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break
        print()