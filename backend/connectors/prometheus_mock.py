"""
Prometheus mock connector.

Returns hard-coded metric data that mirrors the incident fixture.
Replace with real Prometheus HTTP API calls in production.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _metrics_incident() -> List[Dict[str, Any]]:
    return [
        {
            "metric": "http_500_rate",
            "service": "backend",
            "value": 0.08,
            "threshold": 0.01,
            "unit": "ratio",
            "timestamp": "2026-09-25T14:22:00",
            "query": "rate(http_requests_total{status='500'}[5m])",
        },
        {
            "metric": "avg_latency_ms",
            "service": "backend",
            "value": 3200,
            "threshold": 500,
            "unit": "ms",
            "timestamp": "2026-09-25T14:22:00",
            "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        },
        {
            "metric": "cpu_percent",
            "service": "backend",
            "value": 92,
            "threshold": 80,
            "unit": "percent",
            "timestamp": "2026-09-25T14:22:00",
            "query": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
        },
    ]


def _metrics_healthy() -> List[Dict[str, Any]]:
    return [
        {
            "metric": "http_500_rate",
            "service": "backend",
            "value": 0.0,
            "threshold": 0.01,
            "unit": "ratio",
            "timestamp": "2026-09-25T14:07:00",
            "query": "rate(http_requests_total{status='500'}[5m])",
        },
        {
            "metric": "avg_latency_ms",
            "service": "backend",
            "value": 45,
            "threshold": 500,
            "unit": "ms",
            "timestamp": "2026-09-25T14:07:00",
            "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        },
        {
            "metric": "cpu_percent",
            "service": "backend",
            "value": 18,
            "threshold": 80,
            "unit": "percent",
            "timestamp": "2026-09-25T14:07:00",
            "query": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
        },
    ]


def fetch_metrics(scenario: str = "incident") -> List[Dict[str, Any]]:
    """
    Return mock Prometheus metric data.

    Args:
        scenario: "incident" or "healthy"

    Returns:
        List of raw metric dicts with fields: metric, service, value,
        threshold, unit, timestamp, query.
    """
    if scenario == "healthy":
        return _metrics_healthy()
    return _metrics_incident()
