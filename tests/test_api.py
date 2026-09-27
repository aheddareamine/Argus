"""
Phase 4 tests — FastAPI endpoints.

Uses httpx.AsyncClient with ASGITransport to call endpoints in-process,
no running server required.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.api.store import store


@pytest_asyncio.fixture
async def client():
    """Async test client wired to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset_store():
    """Reset the store to the healthy fixture before every test."""
    store.load_fixture("healthy")
    yield
    store.load_fixture("healthy")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestHealthProbe:
    async def test_returns_200(self, client):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_returns_ok_status(self, client):
        r = await client.get("/health")
        assert r.json()["status"] == "ok"

    async def test_returns_scenario_field(self, client):
        r = await client.get("/health")
        assert "scenario" in r.json()


# ---------------------------------------------------------------------------
# GET /graph — healthy scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGraphHealthy:
    async def test_returns_200(self, client):
        r = await client.get("/graph")
        assert r.status_code == 200

    async def test_has_nodes_and_edges(self, client):
        r = await client.get("/graph")
        data = r.json()
        assert "nodes" in data
        assert "edges" in data

    async def test_nodes_is_list(self, client):
        r = await client.get("/graph")
        assert isinstance(r.json()["nodes"], list)

    async def test_edges_is_list(self, client):
        r = await client.get("/graph")
        assert isinstance(r.json()["edges"], list)

    async def test_nodes_have_required_fields(self, client):
        r = await client.get("/graph")
        for node in r.json()["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "health" in node

    async def test_edges_have_source_and_target(self, client):
        r = await client.get("/graph")
        for edge in r.json()["edges"]:
            assert "source" in edge
            assert "target" in edge

    async def test_healthy_scenario_no_failing_nodes(self, client):
        r = await client.get("/graph")
        failing = [n for n in r.json()["nodes"] if n["health"] == "FAILING"]
        assert failing == [], f"Unexpected FAILING nodes: {failing}"

    async def test_healthy_scenario_field_is_healthy(self, client):
        r = await client.get("/graph")
        assert r.json()["scenario"] == "healthy"

    async def test_node_health_values_valid(self, client):
        r = await client.get("/graph")
        valid = {"HEALTHY", "DEGRADED", "FAILING", "UNKNOWN"}
        for node in r.json()["nodes"]:
            assert node["health"] in valid


# ---------------------------------------------------------------------------
# GET /graph — incident scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGraphIncident:
    async def test_incident_scenario_has_failing_nodes(self, client):
        await client.post("/demo/incident")
        r = await client.get("/graph")
        failing = [n for n in r.json()["nodes"] if n["health"] == "FAILING"]
        assert len(failing) >= 1

    async def test_incident_scenario_field_is_incident(self, client):
        await client.post("/demo/incident")
        r = await client.get("/graph")
        assert r.json()["scenario"] == "incident"


# ---------------------------------------------------------------------------
# GET /incidents — healthy scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIncidentsListHealthy:
    async def test_returns_200(self, client):
        r = await client.get("/incidents")
        assert r.status_code == 200

    async def test_returns_empty_list_when_healthy(self, client):
        r = await client.get("/incidents")
        assert r.json() == []

    async def test_returns_list(self, client):
        r = await client.get("/incidents")
        assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# GET /incidents — incident scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIncidentsListIncident:
    async def test_returns_incidents_after_switch(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        assert len(r.json()) >= 1

    async def test_incident_has_required_fields(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        inc = r.json()[0]
        for field in ("id", "service", "severity", "status", "start_time",
                      "possible_cause", "evidence", "events"):
            assert field in inc, f"Missing field: {field}"

    async def test_incident_events_sorted_by_timestamp(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        inc = r.json()[0]
        timestamps = [e["timestamp"] for e in inc["events"]]
        assert timestamps == sorted(timestamps)

    async def test_incident_severity_is_critical(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        assert r.json()[0]["severity"] == "critical"

    async def test_incident_status_is_active(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        assert r.json()[0]["status"] == "active"

    async def test_incident_evidence_not_empty(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        assert len(r.json()[0]["evidence"]) >= 2

    async def test_incident_possible_cause_not_empty(self, client):
        await client.post("/demo/incident")
        r = await client.get("/incidents")
        assert r.json()[0]["possible_cause"] != ""


# ---------------------------------------------------------------------------
# GET /incidents/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIncidentDetail:
    async def test_returns_404_for_unknown_id(self, client):
        r = await client.get("/incidents/inc-doesnotexist")
        assert r.status_code == 404

    async def test_returns_200_for_known_id(self, client):
        await client.post("/demo/incident")
        incidents_r = await client.get("/incidents")
        inc_id = incidents_r.json()[0]["id"]
        r = await client.get(f"/incidents/{inc_id}")
        assert r.status_code == 200

    async def test_detail_matches_list_item(self, client):
        await client.post("/demo/incident")
        list_r = await client.get("/incidents")
        inc_id = list_r.json()[0]["id"]
        detail_r = await client.get(f"/incidents/{inc_id}")
        assert detail_r.json()["id"] == inc_id

    async def test_detail_has_events_field(self, client):
        await client.post("/demo/incident")
        list_r = await client.get("/incidents")
        inc_id = list_r.json()[0]["id"]
        detail_r = await client.get(f"/incidents/{inc_id}")
        assert "events" in detail_r.json()
        assert len(detail_r.json()["events"]) >= 1

    async def test_detail_events_have_all_fields(self, client):
        await client.post("/demo/incident")
        list_r = await client.get("/incidents")
        inc_id = list_r.json()[0]["id"]
        detail_r = await client.get(f"/incidents/{inc_id}")
        for ev in detail_r.json()["events"]:
            for field in ("id", "timestamp", "source", "service", "event_type", "status"):
                assert field in ev, f"Event missing field: {field}"

    async def test_detail_has_explanation_field(self, client):
        await client.post("/demo/incident")
        list_r = await client.get("/incidents")
        inc_id = list_r.json()[0]["id"]
        detail_r = await client.get(f"/incidents/{inc_id}")
        assert "explanation" in detail_r.json()


# ---------------------------------------------------------------------------
# POST /demo/{scenario}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDemoSwitch:
    async def test_switch_to_incident_returns_200(self, client):
        r = await client.post("/demo/incident")
        assert r.status_code == 200

    async def test_switch_to_healthy_returns_200(self, client):
        r = await client.post("/demo/healthy")
        assert r.status_code == 200

    async def test_invalid_scenario_returns_422(self, client):
        r = await client.post("/demo/chaos")
        assert r.status_code == 422

    async def test_switch_to_incident_updates_graph(self, client):
        r = await client.post("/demo/incident")
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["scenario"] == "incident"

    async def test_switch_to_incident_returns_incident_count(self, client):
        r = await client.post("/demo/incident")
        assert r.json()["incident_count"] >= 1

    async def test_switch_to_healthy_clears_incidents(self, client):
        await client.post("/demo/incident")
        await client.post("/demo/healthy")
        r = await client.get("/incidents")
        assert r.json() == []

    async def test_toggle_healthy_incident_healthy(self, client):
        """Full round-trip: healthy → incident → healthy."""
        r1 = await client.get("/incidents")
        assert r1.json() == []

        await client.post("/demo/incident")
        r2 = await client.get("/incidents")
        assert len(r2.json()) >= 1

        await client.post("/demo/healthy")
        r3 = await client.get("/incidents")
        assert r3.json() == []

    async def test_graph_reflects_scenario_after_switch(self, client):
        await client.post("/demo/incident")
        graph_r = await client.get("/graph")
        failing = [n for n in graph_r.json()["nodes"] if n["health"] == "FAILING"]
        assert len(failing) >= 1

        await client.post("/demo/healthy")
        graph_r2 = await client.get("/graph")
        failing2 = [n for n in graph_r2.json()["nodes"] if n["health"] == "FAILING"]
        assert failing2 == []
