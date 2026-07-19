import importlib
import pkgutil

from tools.base import Tool
from tools.registry import ToolRegistry

_SKIP = {"base", "registry", "loader"}


def load_tools() -> ToolRegistry:
    registry = ToolRegistry()

    import tools as pkg
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        if name in _SKIP:
            continue
        module = importlib.import_module(f"tools.{name}")
        for attr in dir(module):
            cls = getattr(module, attr)
            if(isinstance(cls, type) and issubclass(cls, Tool) and cls is not Tool):
                registry.register(cls())

    return registry