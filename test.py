import os
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv

from bearclaw.mini_agent import history


load_dotenv()

# 常量
MODEL = "deepseek-v4-flash"
WORKDIR = os.getcwd()
SYSTEM = f"你是一个编程助手，你的工作区在{WORKDIR}"

# 客户端
client = Anthropic(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))

# 工具定义
TOOLS: list = [{
    "name": "bash",
    "description": "run a shell command",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}]

# 执行工具
def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, cwd=WORKDIR, shell=True, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out if out else "no output"
    except Exception as e:
        return f"Error: {e}"

# 构建循环
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, tools=TOOLS, max_tokens=4096, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"使用工具：{block.name}, 参数：{block.input}")
                output = run_bash(str(block.input))
                print(f"工具结果：{output}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
        messages.append({"role": "user", "content": results})


# 主函数
if __name__ == "__main__":
    print("welcome")
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
