"""
Detected component — the common output type for all detectors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DetectedComponent:
    """
    Represents a DevOps tool detected in the target project.

    Attributes:
        name:       Human-readable name, e.g. "GitHub Actions"
        connector:  Machine key, e.g. "github_actions", "docker", "kubernetes", "prometheus"
        stage:      Pipeline stage key: "build" | "test" | "deploy" | "container" |
                    "orchestration" | "observability"
        status:     Last-known status: "healthy" | "failing" | "unknown"
        services:   Service names this component is responsible for
        raw_events: Pre-normalised raw event dicts (passed straight to /ingest)
        meta:       Extra context (repo name, workflow file, etc.)
    """
    name: str
    connector: str
    stage: str
    status: str = "unknown"
    services: List[str] = field(default_factory=list)
    raw_events: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
