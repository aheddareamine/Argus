"""
Docker detector.

Looks for Dockerfile or docker-compose.yml in the target project root.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Optional

from argus_cli.models import DetectedComponent


def detect(project_root: pathlib.Path) -> Optional[DetectedComponent]:
    """
    Detect Docker usage in the target project.

    Returns a DetectedComponent if Dockerfile or docker-compose.yml exists.
    """
    has_dockerfile = (project_root / "Dockerfile").exists()
    has_compose   = (
        (project_root / "docker-compose.yml").exists() or
        (project_root / "docker-compose.yaml").exists()
    )

    if not has_dockerfile and not has_compose:
        return None

    files_found = []
    if has_dockerfile:
        files_found.append("Dockerfile")
    if has_compose:
        files_found.append("docker-compose.yml")

    now = datetime.now(timezone.utc).isoformat()
    raw_events = [{
        "id": "docker-mock-001",
        "name": "Docker Build",
        "head_branch": "main",
        "head_sha": "abc0001",
        "status": "completed",
        "conclusion": "success",
        "created_at": now,
        "updated_at": now,
        "jobs": [{"name": "build", "conclusion": "success"}],
    }]

    return DetectedComponent(
        name="Docker",
        connector="docker",
        stage="container",
        status="healthy",
        services=["container"],
        raw_events=raw_events,
        meta={"files": files_found},
    )
