from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
ENV_NAME = re.compile(r"^(?:#\s*)?([A-Z][A-Z0-9_]*)=", re.MULTILINE)
MANIFEST_NAME = re.compile(r"^\s+-\s+([A-Z][A-Z0-9_]*)$", re.MULTILINE)


def test_plugin_manifest_declares_every_example_environment_variable():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    manifest = (ROOT / "plugin.yaml").read_text(encoding="utf-8")

    example_names = set(ENV_NAME.findall(env_example))
    manifest_names = set(MANIFEST_NAME.findall(manifest))

    assert example_names <= manifest_names


def test_publish_workflow_requires_a_main_based_release_tag():
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )

    assert 'RELEASE_TARGET" = "main"' in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "origin/main" in workflow
