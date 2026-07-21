from tools.base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def get_schema(self) -> list:
        return [t.to_schema() for t in self._tools.values()]

    def run(self, name: str, **kwargs) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"unknow tool: {name}. available: {list(self._tools.keys())}"
        try:
            return tool.run(**kwargs)
        except Exception as e:
            return f"error run {name}: {e}"

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())