"""
Test runner detector.

Looks for pytest.ini, setup.cfg [tool:pytest], package.json with test script,
Jest config, or any test-related config file.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Optional

from argus_cli.models import DetectedComponent


def detect(project_root: pathlib.Path) -> Optional[DetectedComponent]:
    """
    Detect a test runner in the target project.
    """
    framework = None
    evidence_file = None

    # Pytest
    for name in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"):
        if (project_root / name).exists():
            framework = "pytest"
            evidence_file = name
            break

    # Jest / npm test
    if framework is None:
        pkg = project_root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                if "test" in scripts or "jest" in data.get("devDependencies", {}):
                    framework = "jest"
                    evidence_file = "package.json"
            except Exception:
                pass

    # Vitest
    if framework is None:
        for name in ("vitest.config.ts", "vitest.config.js"):
            if (project_root / name).exists():
                framework = "vitest"
                evidence_file = name
                break

    if framework is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    raw_events = [{
        "id": "test-mock-001",
        "name": "CI/CD Pipeline",
        "head_branch": "main",
        "head_sha": "abc0002",
        "status": "completed",
        "conclusion": "success",
        "created_at": now,
        "updated_at": now,
        "jobs": [{"name": "test", "conclusion": "success"}],
    }]

    return DetectedComponent(
        name=f"Tests ({framework})",
        connector="github_actions",   # normalizer already handles test job events
        stage="test",
        status="healthy",
        services=["tests"],
        raw_events=raw_events,
        meta={"framework": framework, "evidence_file": evidence_file},
    )
