"""
Phase 3 tests — Correlation Engine.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timedelta

import pytest

from backend.models.event import Event
from backend.models.incident import Incident
from backend.correlation.engine import CorrelationEngine, CorrelationRule, RULES

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "backend" / "fixtures"


def load_events(fixture_name: str):
    with open(FIXTURES_DIR / fixture_name) as f:
        raw = json.load(f)
    return [Event(**e) for e in raw]


def make_event(
    event_type: str,
    service: str = "backend",
    status: str = "critical",
    offset_seconds: int = 0,
    base: datetime | None = None,
) -> Event:
    if base is None:
        base = datetime(2026, 9, 25, 14, 20, 0)
    return Event(
        id=f"evt-{event_type}-{offset_seconds}",
        timestamp=base + timedelta(seconds=offset_seconds),
        source="test",
        service=service,
        event_type=event_type,
        status=status,
        details={},
    )


# ---------------------------------------------------------------------------
# Engine — basic behaviour
# ---------------------------------------------------------------------------

class TestCorrelationEngineBasic:
    def test_empty_input_returns_empty(self):
        engine = CorrelationEngine()
        assert engine.ingest([]) == []

    def test_single_event_no_incident(self):
        engine = CorrelationEngine()
        events = [make_event("DEPLOY_FAILED")]
        incidents = engine.ingest(events)
        assert incidents == []

    def test_returns_list_of_incidents(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        result = engine.ingest(events)
        assert isinstance(result, list)
        for inc in result:
            assert isinstance(inc, Incident)

    def test_incident_has_required_fields(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        assert len(incidents) >= 1
        inc = incidents[0]
        assert inc.id.startswith("inc-")
        assert inc.service != ""
        assert inc.severity in ("critical", "warning")
        assert inc.status == "active"
        assert inc.start_time is not None
        assert len(inc.events) >= 2
        assert inc.possible_cause != ""
        assert len(inc.evidence) >= 2


# ---------------------------------------------------------------------------
# Primary rule: deployment_cascade_failure
# ---------------------------------------------------------------------------

class TestDeploymentCascadeRule:
    def test_incident_fixture_produces_incident(self):
        """The incident fixture must produce at least one incident."""
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        assert len(incidents) >= 1

    def test_incident_fixture_marks_backend_service(self):
        """At least one incident must be associated with the backend/deploy chain."""
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        services = {i.service for i in incidents}
        # The primary incident starts with DEPLOY_FAILED on 'deploy'
        assert "deploy" in services or "backend" in services

    def test_three_event_chain_produces_incident(self):
        """DEPLOY_FAILED → POD_FAILED → HIGH_ERROR_RATE within window → incident."""
        engine = CorrelationEngine()
        events = [
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
            make_event("POD_FAILED", service="backend", offset_seconds=60),
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=120),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1

    def test_chain_outside_window_no_incident(self):
        """Same chain but spread over 10 minutes should NOT produce an incident."""
        engine = CorrelationEngine(window_seconds=300)
        events = [
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
            make_event("POD_FAILED", service="backend", offset_seconds=400),
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=700),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) == 0

    def test_incident_severity_is_critical(self):
        engine = CorrelationEngine()
        events = [
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
            make_event("POD_FAILED", service="backend", offset_seconds=60),
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=120),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1
        assert incidents[0].severity == "critical"

    def test_incident_events_sorted_by_timestamp(self):
        engine = CorrelationEngine()
        events = [
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=120),
            make_event("POD_FAILED", service="backend", offset_seconds=60),
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1
        ts = [e.timestamp for e in incidents[0].events]
        assert ts == sorted(ts)

    def test_incident_contains_deploy_failed_event(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        all_event_types = {e.event_type for i in incidents for e in i.events}
        assert "DEPLOY_FAILED" in all_event_types


# ---------------------------------------------------------------------------
# Full deployment+DB cascade rule
# ---------------------------------------------------------------------------

class TestDeploymentDbCascadeRule:
    def test_four_event_chain_produces_incident(self):
        """DEPLOY_FAILED → POD_FAILED → DATABASE_CONNECTION_ERROR → HIGH_ERROR_RATE."""
        engine = CorrelationEngine()
        events = [
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
            make_event("POD_FAILED", service="backend", offset_seconds=60),
            make_event("DATABASE_CONNECTION_ERROR", service="database", offset_seconds=90),
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=120),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1

    def test_possible_cause_mentions_database(self):
        engine = CorrelationEngine()
        events = [
            make_event("DEPLOY_FAILED", service="deploy", offset_seconds=0),
            make_event("POD_FAILED", service="backend", offset_seconds=60),
            make_event("DATABASE_CONNECTION_ERROR", service="database", offset_seconds=90),
            make_event("HIGH_ERROR_RATE", service="backend", offset_seconds=120),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1
        cause = incidents[0].possible_cause.lower()
        assert "database" in cause or "deployment" in cause

    def test_incident_fixture_full_chain(self):
        """The full incident fixture (5 events) should produce exactly one incident."""
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        assert len(incidents) == 1

    def test_evidence_list_not_empty(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        assert len(incidents) >= 1
        assert len(incidents[0].evidence) >= 2

    def test_evidence_contains_deploy_failed_label(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        evidence_text = " ".join(incidents[0].evidence).lower()
        assert "deployment" in evidence_text or "deploy" in evidence_text


# ---------------------------------------------------------------------------
# Pod + App error rule
# ---------------------------------------------------------------------------

class TestPodAppErrorRule:
    def test_pod_app_error_chain(self):
        engine = CorrelationEngine()
        events = [
            make_event("POD_FAILED", service="backend", offset_seconds=0),
            make_event("APPLICATION_ERROR", service="backend", offset_seconds=30),
        ]
        incidents = engine.ingest(events)
        assert len(incidents) >= 1

    def test_pod_app_error_same_service(self):
        engine = CorrelationEngine()
        events = [
            make_event("POD_FAILED", service="backend", offset_seconds=0),
            make_event("APPLICATION_ERROR", service="backend", offset_seconds=30),
        ]
        incidents = engine.ingest(events)
        assert incidents[0].service == "backend"


# ---------------------------------------------------------------------------
# Healthy fixture — must NOT produce incidents
# ---------------------------------------------------------------------------

class TestHealthyFixtureNoIncidents:
    def test_healthy_fixture_produces_no_incidents(self):
        engine = CorrelationEngine()
        events = load_events("fixture-healthy.json")
        incidents = engine.ingest(events)
        assert incidents == [], f"Expected no incidents, got: {incidents}"


# ---------------------------------------------------------------------------
# Event deduplication — events only appear in one incident
# ---------------------------------------------------------------------------

class TestEventDeduplication:
    def test_events_not_reused_across_incidents(self):
        engine = CorrelationEngine()
        events = load_events("fixture-incident.json")
        incidents = engine.ingest(events)
        all_event_ids = [e.id for i in incidents for e in i.events]
        assert len(all_event_ids) == len(set(all_event_ids)), "Duplicate event IDs across incidents"


# ---------------------------------------------------------------------------
# Rules data integrity
# ---------------------------------------------------------------------------

class TestRulesIntegrity:
    def test_rules_list_not_empty(self):
        assert len(RULES) >= 2

    def test_each_rule_has_chain_of_at_least_two(self):
        for rule in RULES:
            assert len(rule.chain) >= 2, f"Rule {rule.name} chain too short"

    def test_each_rule_has_possible_cause(self):
        for rule in RULES:
            assert rule.possible_cause != "", f"Rule {rule.name} missing possible_cause"

    def test_severity_values_valid(self):
        for rule in RULES:
            assert rule.severity in ("critical", "warning"), f"Invalid severity in {rule.name}"
