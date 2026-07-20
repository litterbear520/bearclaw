import os
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()

# 常量
MODEL = "deepseek-v4-flash"
SYSTEM = f"你是一个编程智能体，你的工作区在{os.getcwd()}"

# 客户端
client = Anthropic(api_key=os.getenv("LLM_API_KEY"), base_url="https://api.deepseek.com/anthropic")

# 工具定义
TOOLS: list = [{
    "name": "bash",
    "description": "Run a shell command",
    "input_schema":{
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}]

# 工具执行
def run_bash(command) -> str:
    try:
        r = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=120, cwd=os.getcwd())
        out = (r.stdout + r.stderr).strip()
        return out if out else "no output"
    except Exception as e:
        return f"Error: {e}"


# 循环构建
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages, max_tokens=4096, tools=TOOLS
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"使用工具：{block.name}, 参数：{block.input}")
                out = run_bash(**block.input)
                print(f"工具结果：{out}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": out
                })
        messages.append({"role": "user", "content": results})


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
        response = history[-1]["content"]
        if isinstance(response, list):
            for block in response:
                if block.type == "text":
                    print(block.text)
        print()