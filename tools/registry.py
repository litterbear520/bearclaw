from tools.base import Tool


class ToolRegistry:
    # 初始化工具字典
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    # 注册
    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    # 获取
    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    # 验证
    def has(self, name: str) -> bool:
        return name in self._tools

    # 获取schema
    def get_schema(self) -> list:
        return [t.to_schema() for t in self._tools.values()]

    # 运行
    def run(self, name: str, **kwargs) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"unknow tool: {name}. available: {list(self._tools.keys())}"
        try:
            return tool.run(**kwargs)
        except Exception as e:
            return f"error run {name}: {e}"

    # 获取所有工具名
    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())