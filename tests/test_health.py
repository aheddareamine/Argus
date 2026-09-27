"""
Phase 3 tests — Health Engine.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timedelta

import pytest

from backend.models.event import Event
from backend.models.incident import Incident
from backend.correlation.engine import CorrelationEngine
from backend.health.health_engine import (
    compute_health,
    get_graph_data,
    SERVICES,
    TOPOLOGY_EDGES,
)

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "backend" / "fixtures"


def load_events(fixture_name: str):
    with open(FIXTURES_DIR / fixture_name) as f:
        raw = json.load(f)
    return [Event(**e) for e in raw]


def make_event(
    event_type: str,
    service: str,
    status: str = "ok",
    offset_seconds: int = 0,
) -> Event:
    base = datetime(2026, 9, 25, 14, 0, 0)
    return Event(
        id=f"evt-{service}-{event_type}-{offset_seconds}",
        timestamp=base + timedelta(seconds=offset_seconds),
        source="test",
        service=service,
        event_type=event_type,
        status=status,
        details={},
    )


def make_incident(
    service: str,
    severity: str = "critical",
    events: list | None = None,
) -> Incident:
    return Incident(
        id=f"inc-{service}",
        service=service,
        severity=severity,  # type: ignore[arg-type]
        status="active",
        start_time=datetime(2026, 9, 25, 14, 20, 0),
        events=events or [],
        possible_cause="test",
        evidence=["test"],
    )


# ---------------------------------------------------------------------------
# compute_health — healthy fixture
# ---------------------------------------------------------------------------

class TestComputeHealthHealthy:
    def test_healthy_fixture_all_known_services_have_status(self):
        events = load_events("fixture-healthy.json")
        health = compute_health(events, [])
        for service in SERVICES:
            assert service in health

    def test_healthy_fixture_no_critical_statuses(self):
        events = load_events("fixture-healthy.json")
        health = compute_health(events, [])
        for service, status in health.items():
            assert status != "FAILING", f"{service} should not be FAILING in healthy scenario"

    def test_healthy_fixture_build_is_healthy(self):
        events = load_events("fixture-healthy.json")
        health = compute_health(events, [])
        assert health["build"] == "HEALTHY"

    def test_healthy_fixture_backend_is_healthy(self):
        events = load_events("fixture-healthy.json")
        health = compute_health(events, [])
        assert health["backend"] == "HEALTHY"

    def test_no_incidents_no_failing(self):
        events = [make_event("POD_STARTED", "backend", status="ok")]
        health = compute_health(events, [])
        assert health["backend"] == "HEALTHY"


# ---------------------------------------------------------------------------
# compute_health — incident fixture
# ---------------------------------------------------------------------------

class TestComputeHealthIncident:
    def test_incident_fixture_with_correlation_has_failing_service(self):
        events = load_events("fixture-incident.json")
        engine = CorrelationEngine()
        incidents = engine.ingest(events)
        health = compute_health(events, incidents)
        failing = [s for s, h in health.items() if h == "FAILING"]
        assert len(failing) >= 1, f"Expected at least one FAILING service, got: {health}"

    def test_incident_fixture_deploy_or_backend_is_failing(self):
        events = load_events("fixture-incident.json")
        engine = CorrelationEngine()
        incidents = engine.ingest(events)
        health = compute_health(events, incidents)
        assert health.get("deploy") == "FAILING" or health.get("backend") == "FAILING", \
            f"Expected deploy or backend FAILING, got: {health}"

    def test_active_critical_incident_makes_service_failing(self):
        events = [make_event("POD_FAILED", "backend", status="critical")]
        incident = make_incident("backend", severity="critical", events=events)
        health = compute_health(events, [incident])
        assert health["backend"] == "FAILING"

    def test_active_warning_incident_makes_service_degraded(self):
        events = [make_event("HIGH_LATENCY", "backend", status="warning")]
        incident = make_incident("backend", severity="warning", events=events)
        health = compute_health(events, [incident])
        assert health["backend"] == "DEGRADED"

    def test_resolved_incident_does_not_affect_health(self):
        events = [make_event("POD_STARTED", "backend", status="ok")]
        incident = make_incident("backend", severity="critical")
        incident.status = "resolved"  # type: ignore[assignment]
        health = compute_health(events, [incident])
        # resolved incident should not mark service as FAILING
        assert health["backend"] != "FAILING"


# ---------------------------------------------------------------------------
# compute_health — event-driven rules
# ---------------------------------------------------------------------------

class TestComputeHealthEventDriven:
    def test_last_success_event_means_healthy(self):
        events = [
            make_event("POD_FAILED", "backend", status="critical", offset_seconds=0),
            make_event("POD_STARTED", "backend", status="ok", offset_seconds=60),
        ]
        health = compute_health(events, [])
        assert health["backend"] == "HEALTHY"

    def test_last_critical_event_means_failing(self):
        events = [
            make_event("POD_STARTED", "backend", status="ok", offset_seconds=0),
            make_event("POD_FAILED", "backend", status="critical", offset_seconds=60),
        ]
        health = compute_health(events, [])
        assert health["backend"] == "FAILING"

    def test_no_events_for_service_means_unknown(self):
        health = compute_health([], [])
        assert health.get("database") == "UNKNOWN"

    def test_cross_service_incident_marks_involved_services(self):
        """An incident whose events touch 'backend' and 'database' should mark both."""
        ev_backend = make_event("POD_FAILED", "backend", status="critical")
        ev_db = make_event("DATABASE_CONNECTION_ERROR", "database", status="critical")
        incident = make_incident("backend", severity="critical", events=[ev_backend, ev_db])
        health = compute_health([ev_backend, ev_db], [incident])
        assert health["backend"] == "FAILING"
        assert health["database"] == "FAILING"


# ---------------------------------------------------------------------------
# get_graph_data
# ---------------------------------------------------------------------------

class TestGetGraphData:
    def test_returns_nodes_and_edges(self):
        graph = get_graph_data([], [])
        assert "nodes" in graph
        assert "edges" in graph

    def test_nodes_count_matches_services(self):
        graph = get_graph_data([], [])
        assert len(graph["nodes"]) == len(SERVICES)

    def test_each_node_has_id_label_health(self):
        graph = get_graph_data([], [])
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "health" in node

    def test_edges_match_topology(self):
        graph = get_graph_data([], [])
        edge_pairs = {(e["source"], e["target"]) for e in graph["edges"]}
        for src, tgt in TOPOLOGY_EDGES:
            assert (src, tgt) in edge_pairs

    def test_healthy_fixture_nodes_all_healthy_or_unknown(self):
        events = load_events("fixture-healthy.json")
        graph = get_graph_data(events, [])
        for node in graph["nodes"]:
            assert node["health"] in ("HEALTHY", "UNKNOWN"), \
                f"Node {node['id']} has unexpected health {node['health']!r} in healthy scenario"

    def test_incident_fixture_has_failing_nodes(self):
        events = load_events("fixture-incident.json")
        engine = CorrelationEngine()
        incidents = engine.ingest(events)
        graph = get_graph_data(events, incidents)
        failing = [n for n in graph["nodes"] if n["health"] == "FAILING"]
        assert len(failing) >= 1, f"Expected FAILING nodes in incident scenario, got: {graph['nodes']}"

    def test_node_health_values_are_valid(self):
        events = load_events("fixture-incident.json")
        engine = CorrelationEngine()
        incidents = engine.ingest(events)
        graph = get_graph_data(events, incidents)
        valid = {"HEALTHY", "DEGRADED", "FAILING", "UNKNOWN"}
        for node in graph["nodes"]:
            assert node["health"] in valid, f"Invalid health {node['health']!r} for {node['id']}"


# ---------------------------------------------------------------------------
# Topology integrity
# ---------------------------------------------------------------------------

class TestTopologyIntegrity:
    def test_all_topology_services_in_service_list(self):
        for src, tgt in TOPOLOGY_EDGES:
            assert src in SERVICES, f"{src} not in SERVICES"
            assert tgt in SERVICES, f"{tgt} not in SERVICES"

    def test_no_self_loops(self):
        for src, tgt in TOPOLOGY_EDGES:
            assert src != tgt

    def test_services_list_has_expected_entries(self):
        for expected in ("build", "tests", "deploy", "backend", "database"):
            assert expected in SERVICES
