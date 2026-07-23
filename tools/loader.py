import importlib
import pkgutil

from pathlib import Path
from tools.base import Tool
from tools.registry import ToolRegistry
from tools.context import ToolContext

_SKIP = {"base", "registry", "loader", "context"}


def load_tools(workspace: Path | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    ctx = ToolContext(workspace=(workspace or Path.cwd()).resolve())

    import tools as pkg
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        if name in _SKIP:
            continue
        module = importlib.import_module(f"tools.{name}")
        for attr in dir(module):
            cls = getattr(module, attr)
            if isinstance(cls, type) and issubclass(cls, Tool) and cls is not Tool:
                registry.register(cls.create(ctx))

    return registry