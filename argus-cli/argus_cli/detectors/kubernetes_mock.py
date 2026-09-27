"""
Kubernetes mock detector.

Looks for k8s/ or helm/ directories, or YAML files containing
'kind: Deployment' or 'kind: Pod'. Does NOT call a real cluster.

Generates plausible mock pod/deployment events reusing the patterns
from backend/connectors/kubernetes_mock.py.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from argus_cli.models import DetectedComponent

_KUBE_KINDS = {"Deployment", "Pod", "Service", "StatefulSet", "DaemonSet", "ReplicaSet"}


def _scan_for_k8s_yaml(root: pathlib.Path) -> List[pathlib.Path]:
    """Find YAML files that contain Kubernetes resource kinds."""
    found = []
    for pattern in ("**/*.yml", "**/*.yaml"):
        for path in root.glob(pattern):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if any(f"kind: {kind}" in text for kind in _KUBE_KINDS):
                    found.append(path)
            except Exception:
                pass
    return found


def _make_healthy_events(services: List[str]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    events = []
    for i, svc in enumerate(services):
        events.append({
            "pod": f"{svc}-pod-{i}",
            "namespace": "production",
            "service": svc,
            "phase": "Running",
            "restarts": 0,
            "reason": None,
            "timestamp": now,
            "logs": [],
        })
    return events


def _make_incident_events(services: List[str]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    events = []
    for i, svc in enumerate(services):
        restarts = 8 if i == 0 else 3
        reason = "CrashLoopBackOff" if i == 0 else "OOMKilled"
        logs = (
            ["PostgreSQL connection refused at 10.0.0.5:5432",
             "Error: failed to connect to database after 8 retries"]
            if i == 0 else
            ["FATAL: out of memory", "PostgreSQL connection refused"]
        )
        events.append({
            "pod": f"{svc}-pod-{i}",
            "namespace": "production",
            "service": svc,
            "phase": "Failed",
            "restarts": restarts,
            "reason": reason,
            "timestamp": now,
            "logs": logs,
        })
    return events


def detect(
    project_root: pathlib.Path,
    simulate_incident: bool = False,
) -> Optional[DetectedComponent]:
    """
    Detect Kubernetes manifests in the target project.

    Checks for:
    - k8s/ or helm/ directories
    - YAML files containing kind: Deployment / kind: Pod

    Returns mocked pod events. Does NOT call a real cluster.
    """
    k8s_dir  = project_root / "k8s"
    helm_dir = project_root / "helm"

    k8s_yaml_files = _scan_for_k8s_yaml(project_root)

    if not k8s_dir.exists() and not helm_dir.exists() and not k8s_yaml_files:
        return None

    # Extract service names from manifest file names
    services: List[str] = []
    for path in k8s_yaml_files:
        stem = path.stem.split(".")[0].split("-")[0]
        if stem not in services and stem not in ("kustomization", "values", "chart"):
            services.append(stem)
    if not services:
        services = ["backend", "database"]

    # Generate mock events
    raw_events = (
        _make_incident_events(services)
        if simulate_incident
        else _make_healthy_events(services)
    )

    status = "failing" if simulate_incident else "healthy"
    evidence_paths = [str(p.relative_to(project_root)) for p in k8s_yaml_files[:5]]
    if k8s_dir.exists():
        evidence_paths.insert(0, "k8s/")
    if helm_dir.exists():
        evidence_paths.insert(0, "helm/")

    return DetectedComponent(
        name="Kubernetes",
        connector="kubernetes",
        stage="orchestration",
        status=status,
        services=services,
        raw_events=raw_events,
        meta={
            "files": evidence_paths,
            "simulate_incident": simulate_incident,
        },
    )
