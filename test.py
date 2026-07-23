import os
import subprocess

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

MODEL = "deepseek-v4-flash"
WORKDIR = os.getcwd()
SYSTEM = f"You are a coding agent, you are working at {WORKDIR}"
TOOLS: list = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}]
client = Anthropic(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))


def run_bash(command) -> str:
    try:
        r = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=120, cwd=WORKDIR)
        out = (r.stdout + r.stderr).strip()
        return out if out else "no output"
    except Exception as e:
        return f"Error: {e}"


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, tools=TOOLS, max_tokens=2000, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"ToolUse: {block.name}, Schema: {block.input}")
                output = run_bash(**block.input)
                print(f"ToolResult: {output}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("Welcome!")
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