"""
Argus — FastAPI backend.

Endpoints:
  GET  /health                  liveness probe
  GET  /graph                   nodes + edges with health status
  GET  /incidents               list of active incidents
  GET  /incidents/{id}          single incident with full timeline
  POST /demo/{scenario}         switch demo state (healthy | incident)
  POST /ingest                  receive detected-component payload from CLI
  GET  /pipeline/{project_id}   resolved pipeline order for a project
  POST /sync                    pull from real GitHub connector
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.api.store import store
from backend.health.health_engine import get_graph_data
from backend.normalizer.normalizer import normalize


# ---------------------------------------------------------------------------
# Lifespan — load healthy fixture on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load_fixture("healthy")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pydantic models for ingest payload
# ---------------------------------------------------------------------------

class RawComponentPayload(BaseModel):
    name: str
    connector: str
    stage: str
    status: str = "unknown"
    services: List[str] = []
    raw_events: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}


class IngestPayload(BaseModel):
    project_id: str = "default"
    pipeline: Dict[str, Any] = {}
    components: List[RawComponentPayload] = []


# ---------------------------------------------------------------------------
# In-memory pipeline registry  {project_id → pipeline dict}
# ---------------------------------------------------------------------------
_pipelines: Dict[str, Dict[str, Any]] = {}


app = FastAPI(
    title="Argus — DevOps Health Map",
    description="Live DevOps health graph with event correlation and incident detection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "null",           # file:// origin for direct open
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Liveness / health probe
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health_probe() -> Dict[str, str]:
    return {"status": "ok", "scenario": store.scenario}


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------

@app.get("/graph", tags=["graph"])
def get_graph() -> Dict[str, Any]:
    """
    Returns the current health map as a graph.

    Response shape:
    {
        "nodes": [{"id": str, "label": str, "health": str}, ...],
        "edges": [{"source": str, "target": str}, ...],
        "scenario": str
    }
    """
    graph = get_graph_data(store.events, store.incidents)
    graph["scenario"] = store.scenario
    return graph


# ---------------------------------------------------------------------------
# GET /incidents
# ---------------------------------------------------------------------------

@app.get("/incidents", tags=["incidents"])
def list_incidents() -> List[Dict[str, Any]]:
    """
    Returns all active incidents with their summary.

    Each item includes: id, service, severity, status, start_time,
    possible_cause, evidence, and a sorted event timeline.
    """
    return [_serialize_incident(inc) for inc in store.incidents]


# ---------------------------------------------------------------------------
# GET /incidents/{id}
# ---------------------------------------------------------------------------

@app.get("/incidents/{incident_id}", tags=["incidents"])
def get_incident(incident_id: str) -> Dict[str, Any]:
    """
    Returns full details for a single incident.

    Includes: all events sorted by timestamp, possible_cause, evidence list,
    and the AI explanation field (empty string if not yet populated).
    """
    match = next((i for i in store.incidents if i.id == incident_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found")
    return _serialize_incident(match)


# ---------------------------------------------------------------------------
# POST /sync — pull from real GitHub connector
# ---------------------------------------------------------------------------

@app.post("/sync", tags=["demo"])
def sync_live() -> Dict[str, Any]:
    """
    Pull latest workflow runs from the real GitHub Actions connector,
    normalise, correlate, and refresh the store.

    Requires GITHUB_TOKEN and GITHUB_REPO env vars.
    Falls back to mock data if unavailable.
    """
    import os
    from backend.connectors.github_actions import fetch_runs
    from backend.correlation.engine import CorrelationEngine

    repo  = os.getenv("GITHUB_REPO", "")
    token = os.getenv("GITHUB_TOKEN", "")
    runs  = fetch_runs(repo=repo or "owner/repo", token=token or None)

    all_events = []
    for run in runs:
        all_events.extend(normalize(run, "github_actions"))

    if all_events:
        store.events = all_events
        store.incidents = CorrelationEngine().ingest(all_events)
        store.scenario  = "live"

    graph = get_graph_data(store.events, store.incidents)
    graph["scenario"] = store.scenario
    graph["incident_count"] = len(store.incidents)
    return graph


# ---------------------------------------------------------------------------
# POST /ingest — receive CLI detector payload
# ---------------------------------------------------------------------------

@app.post("/ingest", tags=["cli"])
def ingest(payload: IngestPayload) -> Dict[str, Any]:
    """
    Receive a batch of detected-component payloads from the CLI.

    Each component's raw_events are normalised using the existing normalizer,
    then the correlation + health engines are re-run.
    The resolved pipeline is stored for GET /pipeline/{project_id}.
    """
    from backend.correlation.engine import CorrelationEngine

    # Store pipeline layout for /pipeline endpoint
    if payload.pipeline:
        _pipelines[payload.project_id] = payload.pipeline

    all_events = []
    for comp in payload.components:
        source = comp.connector
        for raw_event in comp.raw_events:
            try:
                events = normalize(raw_event, source)
                all_events.extend(events)
            except Exception:
                pass  # unknown source or malformed — skip silently

    if all_events:
        store.events   = all_events
        store.incidents = CorrelationEngine().ingest(all_events)
        store.scenario  = "live"

    graph = get_graph_data(store.events, store.incidents)
    graph["scenario"] = store.scenario
    graph["incident_count"] = len(store.incidents)
    graph["project_id"] = payload.project_id
    return graph


# ---------------------------------------------------------------------------
# GET /pipeline/{project_id}
# ---------------------------------------------------------------------------

@app.get("/pipeline/{project_id}", tags=["cli"])
def get_pipeline(project_id: str) -> Dict[str, Any]:
    """
    Return the resolved pipeline description for a project.

    The pipeline is stored when the CLI calls POST /ingest.
    Returns an empty pipeline if no data has been received yet.
    """
    pipeline = _pipelines.get(project_id)
    if pipeline is None:
        # Return default fixed topology as fallback
        from backend.health.health_engine import SERVICES, TOPOLOGY_EDGES, compute_health
        health = compute_health(store.events, store.incidents)
        health_map = {"HEALTHY": "HEALTHY", "DEGRADED": "DEGRADED",
                      "FAILING": "FAILING", "UNKNOWN": "UNKNOWN"}
        nodes = [
            {
                "id": svc,
                "label": svc.capitalize(),
                "stage": svc,
                "connector": "generic",
                "health": health.get(svc, "UNKNOWN"),
            }
            for svc in SERVICES
        ]
        edges = [{"source": s, "target": t} for s, t in TOPOLOGY_EDGES]
        pipeline = {
            "project_id": project_id,
            "stages": [],
            "nodes": nodes,
            "edges": edges,
        }
    return pipeline


# ---------------------------------------------------------------------------
# POST /demo/{scenario}
# ---------------------------------------------------------------------------

@app.post("/demo/{scenario}", tags=["demo"])
def switch_demo(scenario: Literal["healthy", "incident"]) -> Dict[str, Any]:
    """
    Switch the in-memory store to the given demo scenario.

    - healthy  → all services green, no incidents
    - incident → cascading failure chain, one critical incident

    Returns the updated /graph response immediately so the frontend
    can refresh in a single round-trip.
    """
    store.load_fixture(scenario)
    graph = get_graph_data(store.events, store.incidents)
    graph["scenario"] = store.scenario
    graph["incident_count"] = len(store.incidents)
    return graph


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _serialize_incident(inc) -> Dict[str, Any]:
    """Convert an Incident model to a JSON-safe dict with a sorted timeline."""
    return {
        "id": inc.id,
        "service": inc.service,
        "severity": inc.severity,
        "status": inc.status,
        "start_time": inc.start_time.isoformat(),
        "possible_cause": inc.possible_cause,
        "evidence": inc.evidence,
        "explanation": inc.explanation,
        "events": [
            {
                "id": ev.id,
                "timestamp": ev.timestamp.isoformat(),
                "source": ev.source,
                "service": ev.service,
                "event_type": ev.event_type,
                "status": ev.status,
                "details": ev.details,
            }
            for ev in sorted(inc.events, key=lambda e: e.timestamp)
        ],
    }


# ---------------------------------------------------------------------------
# Static frontend mounting (if built dist/ exists)
# ---------------------------------------------------------------------------
import pathlib
from fastapi.staticfiles import StaticFiles

_dist_dir = pathlib.Path(__file__).parent.parent.parent / "frontend" / "dist"
if _dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="static")

