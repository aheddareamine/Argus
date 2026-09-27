"""
Kubernetes mock connector.

Returns hard-coded pod/deployment data that mirrors the incident fixture.
Replace with a real kubernetes-client call in production.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List


def _pods_incident() -> List[Dict[str, Any]]:
    return [
        {
            "pod": "backend-7d8f",
            "namespace": "production",
            "service": "backend",
            "phase": "Failed",
            "restarts": 8,
            "reason": "CrashLoopBackOff",
            "timestamp": "2026-09-25T14:21:00",
            "logs": [
                "PostgreSQL connection refused at 10.0.0.5:5432",
                "dial tcp 10.0.0.5:5432: connect: connection refused",
                "Error: failed to connect to database after 8 retries",
            ],
        },
        {
            "pod": "postgres-5a2b",
            "namespace": "production",
            "service": "database",
            "phase": "Failed",
            "restarts": 3,
            "reason": "OOMKilled",
            "timestamp": "2026-09-25T14:21:30",
            "logs": [
                "FATAL: out of memory",
                "PostgreSQL connection refused",
            ],
        },
    ]


def _pods_healthy() -> List[Dict[str, Any]]:
    return [
        {
            "pod": "backend-6f9c",
            "namespace": "production",
            "service": "backend",
            "phase": "Running",
            "restarts": 0,
            "reason": None,
            "timestamp": "2026-09-25T14:06:00",
            "logs": [],
        },
        {
            "pod": "postgres-5a2b",
            "namespace": "production",
            "service": "database",
            "phase": "Running",
            "restarts": 0,
            "reason": None,
            "timestamp": "2026-09-25T14:06:30",
            "logs": [],
        },
    ]


def fetch_pods(scenario: str = "incident") -> List[Dict[str, Any]]:
    """
    Return mock Kubernetes pod data.

    Args:
        scenario: "incident" or "healthy"

    Returns:
        List of raw pod dicts with fields: pod, namespace, service,
        phase, restarts, reason, timestamp, logs.
    """
    if scenario == "healthy":
        return _pods_healthy()
    return _pods_incident()
