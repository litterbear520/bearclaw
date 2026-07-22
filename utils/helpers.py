from pathlib import Path


_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"


def sync_workspace_templates(workspace: Path) -> list[str]:
    added: list[str] = []


    def _write(src: Path, dest: Path) -> None:
        content = src.read_text(encoding="utf-8")
        if dest.exists():
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        added.append(str(dest.relative_to(workspace)))

    for name in ("AGENTS.md", "SOUL.md", "USER.md"):
        _write(_TEMPLATES_ROOT / name, workspace / name)

    return added