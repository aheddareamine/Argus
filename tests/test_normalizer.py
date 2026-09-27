"""
Phase 2 tests — connectors and normalizer.
"""
from __future__ import annotations

import os
import pytest

from backend.models.event import Event
from backend.connectors.github_actions import fetch_runs, _mock_runs, _mock_runs_healthy
from backend.connectors.kubernetes_mock import fetch_pods
from backend.connectors.prometheus_mock import fetch_metrics
from backend.normalizer.normalizer import (
    normalize,
    normalize_github_actions,
    normalize_kubernetes,
    normalize_kubernetes_logs,
    normalize_prometheus,
)


# ---------------------------------------------------------------------------
# Connector tests
# ---------------------------------------------------------------------------

class TestGitHubActionsConnector:
    def test_mock_returns_list(self):
        os.environ["ARGUS_MOCK_GITHUB"] = "true"
        runs = fetch_runs("owner/repo")
        assert isinstance(runs, list)
        assert len(runs) > 0

    def test_mock_run_has_required_fields(self):
        os.environ["ARGUS_MOCK_GITHUB"] = "true"
        runs = fetch_runs("owner/repo")
        run = runs[0]
        assert "id" in run
        assert "conclusion" in run
        assert "jobs" in run

    def test_mock_incident_conclusion_failure(self):
        runs = _mock_runs()
        assert runs[0]["conclusion"] == "failure"

    def test_mock_healthy_conclusion_success(self):
        runs = _mock_runs_healthy()
        assert runs[0]["conclusion"] == "success"

    def test_no_token_falls_back_to_mock(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("ARGUS_MOCK_GITHUB", raising=False)
        runs = fetch_runs("owner/repo", token=None)
        assert isinstance(runs, list)
        assert len(runs) > 0

    def teardown_method(self):
        os.environ.pop("ARGUS_MOCK_GITHUB", None)


class TestKubernetesMockConnector:
    def test_incident_returns_list(self):
        pods = fetch_pods("incident")
        assert isinstance(pods, list)
        assert len(pods) > 0

    def test_healthy_returns_list(self):
        pods = fetch_pods("healthy")
        assert isinstance(pods, list)
        assert len(pods) > 0

    def test_incident_pod_has_restarts(self):
        pods = fetch_pods("incident")
        restarts = [p["restarts"] for p in pods]
        assert any(r > 0 for r in restarts)

    def test_healthy_pod_has_no_restarts(self):
        pods = fetch_pods("healthy")
        for pod in pods:
            assert pod["restarts"] == 0

    def test_incident_pod_has_logs(self):
        pods = fetch_pods("incident")
        logs = [l for p in pods for l in p.get("logs", [])]
        assert len(logs) > 0

    def test_required_fields_present(self):
        for scenario in ("incident", "healthy"):
            for pod in fetch_pods(scenario):
                for field in ("pod", "namespace", "service", "phase", "restarts", "timestamp"):
                    assert field in pod, f"Missing field {field!r} in {scenario} pod"


class TestPrometheusMockConnector:
    def test_incident_returns_list(self):
        metrics = fetch_metrics("incident")
        assert isinstance(metrics, list)
        assert len(metrics) > 0

    def test_healthy_returns_list(self):
        metrics = fetch_metrics("healthy")
        assert isinstance(metrics, list)
        assert len(metrics) > 0

    def test_incident_http_500_above_threshold(self):
        metrics = fetch_metrics("incident")
        http = next(m for m in metrics if m["metric"] == "http_500_rate")
        assert http["value"] > http["threshold"]

    def test_healthy_http_500_below_threshold(self):
        metrics = fetch_metrics("healthy")
        http = next(m for m in metrics if m["metric"] == "http_500_rate")
        assert http["value"] <= http["threshold"]


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------

class TestNormalizeGitHubActions:
    def test_failure_run_produces_deploy_failed(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        types = [e.event_type for e in events]
        assert "DEPLOY_FAILED" in types

    def test_success_run_produces_deploy_success(self):
        raw = _mock_runs_healthy()[0]
        events = normalize_github_actions(raw)
        types = [e.event_type for e in events]
        assert "DEPLOY_SUCCESS" in types

    def test_all_events_are_event_instances(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        for ev in events:
            assert isinstance(ev, Event)

    def test_failure_run_has_build_test_deploy_events(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        types = {e.event_type for e in events}
        assert "BUILD_SUCCESS" in types
        assert "TEST_SUCCESS" in types
        assert "DEPLOY_FAILED" in types

    def test_all_services_assigned(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        services = {e.service for e in events}
        assert services == {"build", "tests", "deploy"}

    def test_failed_event_status_is_critical(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        deploy = next(e for e in events if e.event_type == "DEPLOY_FAILED")
        assert deploy.status == "critical"

    def test_successful_event_status_is_ok(self):
        raw = _mock_runs_healthy()[0]
        events = normalize_github_actions(raw)
        for ev in events:
            assert ev.status == "ok"

    def test_details_contain_run_id(self):
        raw = _mock_runs()[0]
        events = normalize_github_actions(raw)
        for ev in events:
            assert "run_id" in ev.details


class TestNormalizeKubernetes:
    def test_failed_pod_produces_pod_failed(self):
        raw = fetch_pods("incident")[0]
        event = normalize_kubernetes(raw)
        assert event.event_type == "POD_FAILED"

    def test_running_pod_produces_pod_started(self):
        raw = fetch_pods("healthy")[0]
        event = normalize_kubernetes(raw)
        assert event.event_type == "POD_STARTED"

    def test_event_is_event_instance(self):
        raw = fetch_pods("incident")[0]
        event = normalize_kubernetes(raw)
        assert isinstance(event, Event)

    def test_failed_pod_status_is_critical(self):
        raw = fetch_pods("incident")[0]
        event = normalize_kubernetes(raw)
        assert event.status == "critical"

    def test_healthy_pod_status_is_ok(self):
        raw = fetch_pods("healthy")[0]
        event = normalize_kubernetes(raw)
        assert event.status == "ok"

    def test_details_have_pod_and_restarts(self):
        raw = fetch_pods("incident")[0]
        event = normalize_kubernetes(raw)
        assert "pod" in event.details
        assert "restarts" in event.details


class TestNormalizeKubernetesLogs:
    def test_db_error_logs_produce_db_connection_error(self):
        raw = fetch_pods("incident")[0]  # has postgresql log
        events = normalize_kubernetes_logs(raw)
        types = [e.event_type for e in events]
        assert "DATABASE_CONNECTION_ERROR" in types

    def test_healthy_pod_logs_produce_no_events(self):
        raw = fetch_pods("healthy")[0]
        events = normalize_kubernetes_logs(raw)
        assert events == []

    def test_log_events_are_event_instances(self):
        raw = fetch_pods("incident")[0]
        events = normalize_kubernetes_logs(raw)
        for ev in events:
            assert isinstance(ev, Event)


class TestNormalizePrometheus:
    def test_above_threshold_returns_event(self):
        raw = fetch_metrics("incident")[0]  # http_500_rate above threshold
        event = normalize_prometheus(raw)
        assert event is not None
        assert isinstance(event, Event)

    def test_below_threshold_returns_none(self):
        raw = fetch_metrics("healthy")[0]  # http_500_rate = 0.0, below threshold
        event = normalize_prometheus(raw)
        assert event is None

    def test_http_500_maps_to_high_error_rate(self):
        raw = fetch_metrics("incident")[0]
        event = normalize_prometheus(raw)
        assert event.event_type == "HIGH_ERROR_RATE"

    def test_latency_maps_to_high_latency(self):
        raw = next(m for m in fetch_metrics("incident") if m["metric"] == "avg_latency_ms")
        event = normalize_prometheus(raw)
        assert event is not None
        assert event.event_type == "HIGH_LATENCY"

    def test_details_contain_metric_and_value(self):
        raw = fetch_metrics("incident")[0]
        event = normalize_prometheus(raw)
        assert "metric" in event.details
        assert "value" in event.details


class TestNormalizeDispatcher:
    def test_github_actions_dispatch(self):
        raw = _mock_runs()[0]
        events = normalize(raw, "github_actions")
        assert isinstance(events, list)
        assert len(events) > 0

    def test_kubernetes_dispatch(self):
        raw = fetch_pods("incident")[0]
        events = normalize(raw, "kubernetes")
        assert isinstance(events, list)
        assert len(events) > 0

    def test_prometheus_dispatch_above_threshold(self):
        raw = fetch_metrics("incident")[0]
        events = normalize(raw, "prometheus")
        assert isinstance(events, list)
        assert len(events) == 1

    def test_prometheus_dispatch_below_threshold(self):
        raw = fetch_metrics("healthy")[0]
        events = normalize(raw, "prometheus")
        assert events == []

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="Unknown source"):
            normalize({"foo": "bar"}, "unknown_tool")

    def test_all_returned_items_are_events(self):
        for raw, source in [
            (_mock_runs()[0], "github_actions"),
            (fetch_pods("incident")[0], "kubernetes"),
            (fetch_metrics("incident")[0], "prometheus"),
        ]:
            events = normalize(raw, source)
            for ev in events:
                assert isinstance(ev, Event), f"Not an Event: {ev!r}"
