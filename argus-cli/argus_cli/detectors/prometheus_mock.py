"""
Prometheus mock detector.

Looks for prometheus.yml or a monitoring/ directory referencing Prometheus.
Generates mocked metric events. Does NOT call a real Prometheus instance.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from argus_cli.models import DetectedComponent


def _scan_for_prometheus(root: pathlib.Path) -> List[pathlib.Path]:
    """Find files that suggest Prometheus is configured."""
    found = []
    # Direct config file
    for name in ("prometheus.yml", "prometheus.yaml"):
        p = root / name
        if p.exists():
            found.append(p)

    # monitoring/ directory with any reference to prometheus
    monitoring = root / "monitoring"
    if monitoring.exists():
        for path in monitoring.glob("**/*.yml"):
            try:
                if "prometheus" in path.read_text(encoding="utf-8", errors="ignore").lower():
                    found.append(path)
            except Exception:
                pass

    return found


def _make_healthy_events(services: List[str]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "metric": "http_500_rate",
            "service": svc,
            "value": 0.0,
            "threshold": 0.01,
            "unit": "ratio",
            "timestamp": now,
            "query": "rate(http_requests_total{status='500'}[5m])",
        }
        for svc in services
    ]


def _make_incident_events(services: List[str]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    events = []
    for svc in services:
        events.extend([
            {
                "metric": "http_500_rate",
                "service": svc,
                "value": 0.08,
                "threshold": 0.01,
                "unit": "ratio",
                "timestamp": now,
                "query": "rate(http_requests_total{status='500'}[5m])",
            },
            {
                "metric": "avg_latency_ms",
                "service": svc,
                "value": 3200,
                "threshold": 500,
                "unit": "ms",
                "timestamp": now,
                "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            },
        ])
    return events


def detect(
    project_root: pathlib.Path,
    simulate_incident: bool = False,
) -> Optional[DetectedComponent]:
    """
    Detect Prometheus configuration in the target project.

    Returns mocked metric events. Does NOT call a real Prometheus instance.
    """
    found_files = _scan_for_prometheus(project_root)
    if not found_files:
        return None

    services = ["backend"]

    raw_events = (
        _make_incident_events(services)
        if simulate_incident
        else _make_healthy_events(services)
    )

    status = "failing" if simulate_incident else "healthy"

    return DetectedComponent(
        name="Prometheus",
        connector="prometheus",
        stage="observability",
        status=status,
        services=services,
        raw_events=raw_events,
        meta={
            "files": [str(p.relative_to(project_root)) for p in found_files[:5]],
            "simulate_incident": simulate_incident,
        },
    )
