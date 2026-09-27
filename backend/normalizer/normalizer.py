"""
Normalizer — converts raw connector output into the standard Event schema.

Each source has its own normalize_* function.
The top-level normalize() dispatches by source name.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.models.event import Event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    return f"evt-{uuid.uuid4().hex[:8]}"


def _parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp string, handling trailing Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# GitHub Actions
# ---------------------------------------------------------------------------

def normalize_github_actions(raw: Dict[str, Any]) -> List[Event]:
    """
    Convert a single GitHub Actions workflow run dict into one or more Events.

    A run with conclusion "failure" becomes DEPLOY_FAILED (or BUILD_FAILED /
    TEST_FAILED depending on which job failed).  A successful run becomes
    BUILD_SUCCESS + TEST_SUCCESS + DEPLOY_SUCCESS.
    """
    events: List[Event] = []

    run_id = str(raw.get("id", _make_id()))
    branch = raw.get("head_branch", "main")
    sha = raw.get("head_sha", "")
    conclusion = (raw.get("conclusion") or "").lower()
    timestamp_raw = raw.get("updated_at") or raw.get("created_at") or _now_iso()
    timestamp = _parse_ts(timestamp_raw)

    jobs: List[Dict[str, Any]] = raw.get("jobs", [])

    if jobs:
        # Derive per-job events
        job_map = {j["name"].lower(): j.get("conclusion", "").lower() for j in jobs}

        # Build step
        build_conclusion = job_map.get("build", conclusion)
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="github_actions",
            service="build",
            event_type="BUILD_SUCCESS" if build_conclusion == "success" else "BUILD_FAILED",
            status="ok" if build_conclusion == "success" else "critical",
            details={"run_id": run_id, "branch": branch, "commit": sha},
        ))

        # Test step
        test_conclusion = job_map.get("test", conclusion)
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="github_actions",
            service="tests",
            event_type="TEST_SUCCESS" if test_conclusion == "success" else "TEST_FAILED",
            status="ok" if test_conclusion == "success" else "critical",
            details={"run_id": run_id, "branch": branch},
        ))

        # Deploy step
        deploy_conclusion = job_map.get("deploy", conclusion)
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="github_actions",
            service="deploy",
            event_type="DEPLOY_SUCCESS" if deploy_conclusion == "success" else "DEPLOY_FAILED",
            status="ok" if deploy_conclusion == "success" else "critical",
            details={
                "run_id": run_id,
                "branch": branch,
                "environment": "production",
                "reason": raw.get("conclusion", ""),
            },
        ))
    else:
        # No job breakdown — single event from overall conclusion
        event_type = "DEPLOY_SUCCESS" if conclusion == "success" else "DEPLOY_FAILED"
        status = "ok" if conclusion == "success" else "critical"
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="github_actions",
            service="deploy",
            event_type=event_type,
            status=status,
            details={"run_id": run_id, "branch": branch, "commit": sha},
        ))

    return events


# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------

def normalize_kubernetes(raw: Dict[str, Any]) -> Event:
    """
    Convert a single Kubernetes pod dict into one Event.

    phase "Failed" with restarts > 0  → POD_FAILED
    phase "Running" with restarts == 0 → POD_STARTED
    logs containing DB errors          → APPLICATION_ERROR (emitted separately via normalize_kubernetes_logs)
    """
    pod = raw.get("pod", "unknown")
    service = raw.get("service", "unknown")
    phase = (raw.get("phase") or "").lower()
    restarts = int(raw.get("restarts", 0))
    reason = raw.get("reason") or ""
    timestamp = _parse_ts(raw.get("timestamp", _now_iso()))

    if phase == "failed" or restarts > 0:
        event_type = "POD_FAILED"
        status = "critical"
    else:
        event_type = "POD_STARTED"
        status = "ok"

    return Event(
        id=_make_id(),
        timestamp=timestamp,
        source="kubernetes",
        service=service,
        event_type=event_type,
        status=status,
        details={
            "pod": pod,
            "namespace": raw.get("namespace", "default"),
            "restarts": restarts,
            "reason": reason,
        },
    )


def normalize_kubernetes_logs(raw: Dict[str, Any]) -> List[Event]:
    """
    Inspect the 'logs' list of a pod dict and emit APPLICATION_ERROR /
    DATABASE_CONNECTION_ERROR events for significant log lines.
    """
    events: List[Event] = []
    logs: List[str] = raw.get("logs", [])
    service = raw.get("service", "unknown")
    pod = raw.get("pod", "unknown")
    timestamp = _parse_ts(raw.get("timestamp", _now_iso()))

    db_keywords = ("connection refused", "postgresql", "database", "dial tcp", "connect:")
    app_keywords = ("error", "exception", "fatal", "failed")

    db_logs = [l for l in logs if any(kw in l.lower() for kw in db_keywords)]
    app_logs = [l for l in logs if any(kw in l.lower() for kw in app_keywords)]

    if db_logs:
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="kubernetes",
            service=service,
            event_type="DATABASE_CONNECTION_ERROR",
            status="critical",
            details={"pod": pod, "log": db_logs[0], "occurrences": len(db_logs)},
        ))

    if app_logs and not db_logs:
        # Only emit APPLICATION_ERROR if there isn't already a DB error (avoid duplicate)
        events.append(Event(
            id=_make_id(),
            timestamp=timestamp,
            source="kubernetes",
            service=service,
            event_type="APPLICATION_ERROR",
            status="critical",
            details={"pod": pod, "log": app_logs[0], "occurrences": len(app_logs)},
        ))

    return events


# ---------------------------------------------------------------------------
# Prometheus
# ---------------------------------------------------------------------------

_PROMETHEUS_METRIC_MAP: Dict[str, str] = {
    "http_500_rate": "HIGH_ERROR_RATE",
    "avg_latency_ms": "HIGH_LATENCY",
    "cpu_percent": "HIGH_CPU",
    "memory_percent": "HIGH_MEMORY",
}


def normalize_prometheus(raw: Dict[str, Any]) -> Event | None:
    """
    Convert a single Prometheus metric dict into an Event.

    Only emits an event if the value exceeds the threshold.
    Returns None if within normal range.
    """
    metric_name = raw.get("metric", "")
    value = float(raw.get("value", 0))
    threshold = float(raw.get("threshold", float("inf")))
    service = raw.get("service", "unknown")
    timestamp = _parse_ts(raw.get("timestamp", _now_iso()))

    if value <= threshold:
        return None  # within normal range — no event needed

    event_type = _PROMETHEUS_METRIC_MAP.get(metric_name, "HIGH_ERROR_RATE")

    return Event(
        id=_make_id(),
        timestamp=timestamp,
        source="prometheus",
        service=service,
        event_type=event_type,
        status="critical",
        details={
            "metric": metric_name,
            "value": value,
            "threshold": threshold,
            "unit": raw.get("unit", ""),
            "query": raw.get("query", ""),
        },
    )


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def normalize(raw: Dict[str, Any], source: str) -> List[Event]:
    """
    Normalize a single raw connector payload into a list of Events.

    Args:
        raw:    Raw dict from a connector.
        source: One of "github_actions", "kubernetes", "prometheus".

    Returns:
        List of normalized Event objects (may be empty if nothing is notable).
    """
    if source == "github_actions":
        return normalize_github_actions(raw)

    if source == "kubernetes":
        events = [normalize_kubernetes(raw)]
        events.extend(normalize_kubernetes_logs(raw))
        return [e for e in events if e is not None]

    if source == "prometheus":
        event = normalize_prometheus(raw)
        return [event] if event is not None else []

    raise ValueError(f"Unknown source: {source!r}")
