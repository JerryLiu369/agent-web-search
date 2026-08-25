from __future__ import annotations

import re
from pathlib import Path

from agent_web_search import __version__

ROOT = Path(__file__).resolve().parents[1]


def _match_version(path: Path, pattern: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match is not None, f"Version not found in {path.name}"
    return match.group(1)


def test_project_versions_match() -> None:
    pyproject_version = _match_version(
        ROOT / "pyproject.toml",
        r'^\[project\].*?^version\s*=\s*"([^"]+)"',
    )
    plugin_version = _match_version(
        ROOT / "plugin.yaml",
        r"^version:\s*([^\s]+)",
    )

    assert pyproject_version == plugin_version == __version__
