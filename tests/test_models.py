"""
Phase 1 tests — verify that both fixture files parse cleanly into Pydantic models.
"""
import json
import pathlib
import pytest

from backend.models.event import Event
from backend.models.incident import Incident

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "backend" / "fixtures"


def load_fixture(name: str):
    path = FIXTURES_DIR / name
    with open(path) as f:
        return json.load(f)


class TestEventModel:
    def test_event_fields_exist(self):
        event = Event(
            id="evt-test-001",
            timestamp="2026-09-25T14:00:00",
            source="github_actions",
            service="backend",
            event_type="DEPLOY_FAILED",
            status="critical",
            details={"reason": "timeout"},
        )
        assert event.id == "evt-test-001"
        assert event.service == "backend"
        assert event.event_type == "DEPLOY_FAILED"
        assert event.status == "critical"
        assert event.details["reason"] == "timeout"

    def test_event_defaults_empty_details(self):
        event = Event(
            id="evt-test-002",
            timestamp="2026-09-25T14:00:00",
            source="kubernetes",
            service="database",
            event_type="POD_STARTED",
            status="ok",
        )
        assert event.details == {}

    def test_invalid_event_type_raises(self):
        with pytest.raises(Exception):
            Event(
                id="evt-bad",
                timestamp="2026-09-25T14:00:00",
                source="unknown",
                service="backend",
                event_type="NOT_A_REAL_EVENT",
                status="ok",
            )

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            Event(
                id="evt-bad",
                timestamp="2026-09-25T14:00:00",
                source="kubernetes",
                service="backend",
                event_type="POD_FAILED",
                status="super_critical",
            )


class TestIncidentModel:
    def test_incident_defaults(self):
        from datetime import datetime

        incident = Incident(
            id="inc-001",
            service="backend",
            severity="critical",
            start_time=datetime(2026, 9, 25, 14, 20),
        )
        assert incident.status == "active"
        assert incident.events == []
        assert incident.evidence == []
        assert incident.possible_cause == ""
        assert incident.explanation == ""

    def test_incident_with_events(self):
        from datetime import datetime

        ev = Event(
            id="evt-001",
            timestamp=datetime(2026, 9, 25, 14, 20),
            source="github_actions",
            service="deploy",
            event_type="DEPLOY_FAILED",
            status="critical",
        )
        incident = Incident(
            id="inc-002",
            service="backend",
            severity="critical",
            start_time=datetime(2026, 9, 25, 14, 20),
            events=[ev],
            possible_cause="Deployment triggered pod crash",
            evidence=["DEPLOY_FAILED", "POD_FAILED"],
        )
        assert len(incident.events) == 1
        assert incident.events[0].event_type == "DEPLOY_FAILED"
        assert len(incident.evidence) == 2


class TestFixtureHealthy:
    def test_all_events_parse(self):
        raw = load_fixture("fixture-healthy.json")
        assert len(raw) > 0
        events = [Event(**e) for e in raw]
        assert len(events) == len(raw)

    def test_all_statuses_ok(self):
        raw = load_fixture("fixture-healthy.json")
        events = [Event(**e) for e in raw]
        for ev in events:
            assert ev.status == "ok", f"Expected ok, got {ev.status} for {ev.id}"

    def test_no_critical_events(self):
        raw = load_fixture("fixture-healthy.json")
        events = [Event(**e) for e in raw]
        critical = [e for e in events if e.status == "critical"]
        assert critical == [], f"Found critical events in healthy fixture: {critical}"


class TestFixtureIncident:
    def test_all_events_parse(self):
        raw = load_fixture("fixture-incident.json")
        assert len(raw) > 0
        events = [Event(**e) for e in raw]
        assert len(events) == len(raw)

    def test_has_deploy_failed(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        types = [e.event_type for e in events]
        assert "DEPLOY_FAILED" in types

    def test_has_pod_failed(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        types = [e.event_type for e in events]
        assert "POD_FAILED" in types

    def test_has_high_error_rate(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        types = [e.event_type for e in events]
        assert "HIGH_ERROR_RATE" in types

    def test_all_critical(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        for ev in events:
            assert ev.status == "critical", f"Expected critical, got {ev.status} for {ev.id}"

    def test_timestamps_ordered(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps), "Incident events are not in chronological order"

    def test_incident_window_under_5_minutes(self):
        raw = load_fixture("fixture-incident.json")
        events = [Event(**e) for e in raw]
        delta = events[-1].timestamp - events[0].timestamp
        assert delta.total_seconds() <= 300, f"Incident window too wide: {delta}"
