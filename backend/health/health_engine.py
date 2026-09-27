"""
Health Engine — derives per-service health status from events and incidents.

Health states (from spec):
  HEALTHY   — no active incidents, last event for service was a success
  DEGRADED  — active warning-severity incident, or recent non-critical errors
  FAILING   — active critical-severity incident
  UNKNOWN   — no data for this service
"""
from __future__ import annotations

from typing import Dict, List, Literal

from backend.models.event import Event
from backend.models.incident import Incident


HealthStatus = Literal["HEALTHY", "DEGRADED", "FAILING", "UNKNOWN"]

# Fixed service topology — order matters for graph edges
SERVICES: List[str] = ["build", "tests", "deploy", "backend", "database"]

# Edges: (source, target) — defines the dependency graph
TOPOLOGY_EDGES: List[tuple[str, str]] = [
    ("build", "tests"),
    ("tests", "deploy"),
    ("deploy", "backend"),
    ("backend", "database"),
]

# Event types that indicate a service is healthy when they are the last event
_SUCCESS_TYPES = {
    "BUILD_SUCCESS",
    "TEST_SUCCESS",
    "DEPLOY_SUCCESS",
    "POD_STARTED",
}

# Event types that indicate a service is failing
_CRITICAL_TYPES = {
    "BUILD_FAILED",
    "TEST_FAILED",
    "DEPLOY_FAILED",
    "POD_FAILED",
    "POD_RESTARTED",
    "APPLICATION_ERROR",
    "DATABASE_CONNECTION_ERROR",
    "HIGH_ERROR_RATE",
    "HIGH_CPU",
    "HIGH_MEMORY",
    "HIGH_LATENCY",
}


def compute_health(
    events: List[Event],
    incidents: List[Incident],
) -> Dict[str, HealthStatus]:
    """
    Compute the health status of every known service.

    Rules (applied in priority order):
      1. Service has an active CRITICAL incident  → FAILING
      2. Service has an active WARNING incident   → DEGRADED
      3. Service's last event is a success type   → HEALTHY
      4. Service's last event is a critical type  → FAILING
      5. Service has events but none match above  → DEGRADED
      6. Service has no events at all             → UNKNOWN

    Args:
        events:    All normalized events in the current store.
        incidents: All active incidents produced by the correlation engine.

    Returns:
        Dict mapping service name → HealthStatus.
    """
    result: Dict[str, HealthStatus] = {}

    # Index incidents by service
    incident_by_service: Dict[str, List[Incident]] = {}
    for inc in incidents:
        if inc.status == "active":
            incident_by_service.setdefault(inc.service, []).append(inc)

        # Also mark services that appear inside the incident's events
        for ev in inc.events:
            if ev.service != inc.service and inc.status == "active":
                incident_by_service.setdefault(ev.service, []).append(inc)

    # Index last event per service
    last_event_by_service: Dict[str, Event] = {}
    for ev in sorted(events, key=lambda e: e.timestamp):
        last_event_by_service[ev.service] = ev

    for service in SERVICES:
        active_incidents = incident_by_service.get(service, [])

        # Rule 1 & 2 — incident-driven
        if active_incidents:
            severities = {i.severity for i in active_incidents}
            if "critical" in severities:
                result[service] = "FAILING"
                continue
            else:
                result[service] = "DEGRADED"
                continue

        # Rules 3–6 — event-driven
        last = last_event_by_service.get(service)
        if last is None:
            result[service] = "UNKNOWN"
        elif last.event_type in _SUCCESS_TYPES:
            result[service] = "HEALTHY"
        elif last.event_type in _CRITICAL_TYPES:
            result[service] = "FAILING"
        else:
            result[service] = "DEGRADED"

    return result


def get_graph_data(
    events: List[Event],
    incidents: List[Incident],
) -> Dict:
    """
    Build the full graph payload for the /graph API endpoint.

    Returns:
        {
            "nodes": [{"id": str, "label": str, "health": HealthStatus}, ...],
            "edges": [{"source": str, "target": str}, ...],
        }
    """
    health = compute_health(events, incidents)

    nodes = [
        {
            "id": service,
            "label": service.capitalize(),
            "health": health.get(service, "UNKNOWN"),
        }
        for service in SERVICES
    ]

    edges = [
        {"source": src, "target": tgt}
        for src, tgt in TOPOLOGY_EDGES
    ]

    return {"nodes": nodes, "edges": edges}
