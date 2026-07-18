import os
import subprocess

from tools.base import Tool


class BashTool(Tool):
    name = "bash"
    description = "Run a shell command"
    params = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def run(self, command: str) -> str:
        try:
            r = subprocess.run(command, capture_output=True, shell=True, text=True, cwd=os.getcwd(), timeout=120)
            out = (r.stdout + r.stderr).strip()
            return out if out else "no output"
        except Exception as e:
            return f"error: {e}"