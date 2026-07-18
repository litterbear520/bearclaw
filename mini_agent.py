import os
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# 常量
MODEL = "deepseek-v4-flash"
SYSTEM = f"你是一个编程智能体，你的工作目录是{os.getcwd()}"
WORKDIR = Path.cwd()

# 客户端
client = Anthropic(api_key=os.getenv("LLM_API_KEY"), base_url="https://api.deepseek.com/anthropic")

# 工具定义
TOOLS: list = [
{
    "name": "bash", 
    "description": "Run a shell command",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
},
{
    "name": "read_file", 
    "description": "Read file contents.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["path"],
    }
},
{
    "name": "write_file", 
    "description": "write content to a file",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }
},
{
    "name": "edit_file", 
    "description": "Replace exact text in a file once",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
        "required": ["path", "old_text", "new_text"],

    }
},
{
    "name": "glob", 
    "description": "Find files matching a glob pattern",
    "input_schema": {
        "type": "object",
        "properties": {"pattern": {"type": "string"}},
        "required": ["pattern"],
    }
},
]


# 路径安全
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径逃离工作区：{p}")
    return path


# bash
def run_bash(command) -> str:
    try:
        r = subprocess.run(command, shell=True, text=True, capture_output=True, cwd=os.getcwd(), timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out if out else "no output"
    except Exception as e:
        return f"error: {e}"


# 读
def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


# 写
def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"写入 {len(content)} 字到 {path}"
    except Exception as e:
        return f"error: {e}"


# 改
def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1)) #  replace 不修改原字符串（字符串不可变），而是返回一个新字符串
        return f"edited {path}"
    except Exception as e:
        return f"error: {e}"


# 匹配
def run_glob(pattern: str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern, root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "no matches"
    except Exception as e:
        return f"error: {e}"


# 工具分发
RUN_TOOLS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob
}


# 循环
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, tools=TOOLS, max_tokens=8000, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return
        
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"使用工具：{block.name}, 参数：{block.input}")
                run = RUN_TOOLS.get(block.name)
                output = run(**block.input) if run else f"unknow: {block.name}"
                print(f"工具结果：{output}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
        messages.append({"role": "user", "content": results})


# 主函数
if __name__ == "__main__":
    print("Welcome come back")
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
