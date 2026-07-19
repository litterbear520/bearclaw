import os

from dotenv import load_dotenv

from tools.loader import load_tools
from providers.factory import make_provider

load_dotenv()

registry = load_tools()
provider = make_provider()

SYSTEM = f"你是一个编程智能体，你的工作区在{os.getcwd()}"


# 循环构建
def agent_loop(messages: list):
    while True:
        response = provider.chat(
            tools=registry.get_schema(), 
            messages=[{"role": "system", "content": SYSTEM}] + messages, 
            max_tokens=10000
        )
        
        ai_msg: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            ai_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.args}}
                for tc in response.tool_calls
            ]
        messages.append(ai_msg)

        if response.finish_reason != "tool_calls":
            return

        for tc in response.tool_calls:
            print(f"使用工具：{tc.name}, 参数：{tc.args}")
            output = registry.run(tc.name, **(tc.args if isinstance(tc.args, dict) else {}))
            print(f"工具结果：{output}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output
            })

        
# 主函数
if __name__ == "__main__":
    print("Welcome to bearclaw!")
    history = []
    while True: 
        try: 
            query = input(">> ")
        except Exception:
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break
        print()