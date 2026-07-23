import glob as g

from pathlib import Path
from tools.base import Tool


def safe_path(workspace: Path, p: str) -> Path:
    path = (workspace / p).resolve()
    if not path.is_relative_to(workspace):
        raise ValueError(f"路径逃离工作区: {p}")
    return path


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read file contents."
    params = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["path"]
    }

    def __init__(self, workspace: Path | None = None):
        self.workspace = (workspace or Path.cwd()).resolve()

    def run(self, path: str, limit: int | None = None) -> str:
        try:
            lines = safe_path(self.workspace, path).read_text().splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... {len(lines) - limit} more lines"]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to file."
    params = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"]
    }

    def __init__(self, workspace: Path | None = None):
        self.workspace = (workspace or Path.cwd()).resolve()

    def run(self, path: str, content: str) -> str:
        try:
            file_path = safe_path(self.workspace, path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return f"写入 {len(content)} 字到 {path}"
        except Exception as e:
            return f"Error: {e}"


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace exact text in a file once"
    params = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"}
        },
        "required": ["path", "old_text", "new_text"]
    }

    def __init__(self, workspace: Path | None = None):
        self.workspace = (workspace or Path.cwd()).resolve()

    def run(self, path: str, old_text: str, new_text: str) -> str:
        try:
            file_path = safe_path(self.workspace, path)
            text = file_path.read_text()
            if old_text not in text:
                return f"Error: text not found in {path}"
            file_path.write_text(text.replace(old_text, new_text, 1))
            return f"Edit {path}"
        except Exception as e:
            return f"Error: {e}"


class GlobTool(Tool):
    name = "glob"
    description = "Find file matching a glob pattern."
    params = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
        },
        "required": ["pattern"]
    }

    def __init__(self, workspace: Path | None = None):
        self.workspace = (workspace or Path.cwd()).resolve()

    def run(self, pattern: str) -> str:
        try:
            results = []
            for match in g.glob(pattern, root_dir=self.workspace):
                if (self.workspace / match).resolve().is_relative_to(self.workspace):
                    results.append(match)
            return "\n".join(results) if results else "no matches"
        except Exception as e:
            return f"Error: {e}"
