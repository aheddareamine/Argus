# Argus — Project Argus Build Plan (24-Hour Hackathon)

> **AI Layer note:** Phase 6 uses a free LLM API (e.g. Groq / OpenRouter / Gemini free tier) instead of IBM Bob. It is a stretch goal — build it only if time permits after Phase 5 is solid.

## Top-Level Overview

**Goal:** Build a live DevOps Health Map that collects events from GitHub Actions, Kubernetes, and Prometheus, normalises them into a common schema, correlates related failures into incidents, and presents the result as an interactive graph with an AI-generated plain-English explanation.

**Scope:** Full stack — Python/FastAPI backend + Vanilla JS / Cytoscape.js frontend + optional IBM Bob AI layer.

**Approach:** Seven sequential phases. Each phase produces a testable, independently runnable slice. Nothing is built on an unverified layer. The MVP uses mock connectors for Kubernetes and Prometheus; only the GitHub Actions connector is real. The AI layer (Phase 6) is additive and does not block the demo.

**Out of scope for 24 h:** OAuth GitHub flow, real Kubernetes cluster connection, Docker connector, persistent database, multi-environment support.

---

## Phase 1 — Foundation: Models, Fixtures, and Project Scaffold

**Status:** `[x] done`

### Intent
Establish the shared data contracts (`Event`, `Incident`, `HealthNode`) that every other layer depends on. Create the two demo fixture files (healthy scenario and incident scenario) that will be used as ground truth throughout development. Set up the project folder structure.

### Expected Outcomes
- `backend/models/event.py` — Pydantic `Event` model with all fields from the spec
- `backend/models/incident.py` — Pydantic `Incident` model
- `backend/fixtures/fixture-healthy.json` — array of normalized events representing a healthy state
- `backend/fixtures/fixture-incident.json` — array of normalized events representing the full incident chain
- `backend/requirements.txt` — all Python dependencies pinned
- `tests/test_models.py` — unit tests that instantiate both models and validate the fixture files parse without errors

### Todo List
1. Create the folder tree: `backend/connectors`, `backend/models`, `backend/normalizer`, `backend/correlation`, `backend/health`, `backend/ai`, `backend/api`, `backend/fixtures`, `tests`, `frontend`
2. Write `backend/models/event.py` — `Event` Pydantic model (`id`, `timestamp`, `source`, `service`, `event_type`, `status`, `details: dict`)
3. Write `backend/models/incident.py` — `Incident` Pydantic model (`id`, `service`, `severity`, `status`, `start_time`, `events: list[Event]`, `possible_cause`, `evidence: list[str]`)
4. Write `backend/fixtures/fixture-healthy.json` — 6 events: BUILD_SUCCESS, TEST_SUCCESS, DEPLOY_SUCCESS, POD_STARTED, DB connection OK, metrics normal
5. Write `backend/fixtures/fixture-incident.json` — 5 events: DEPLOY_FAILED → POD_FAILED → APPLICATION_ERROR → DATABASE connection refused → HIGH_ERROR_RATE, all on the `backend` service, timestamps within a 2-minute window
6. Write `backend/requirements.txt` with: `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `pytest`
7. Write `tests/test_models.py` — load both fixture files, parse each event through the `Event` model, assert no validation errors

### Relevant Context
- Event schema defined in `idees.pdf` §10–11 and `README.md` §Event Types
- Incident structure defined in `idees.pdf` §13
- Fixture scenarios defined in `idees.pdf` §8 (Scenario A and B)

---

## Phase 2 — Data Pipeline: Connectors and Normalizer

**Status:** `[x] done`

### Intent
Build the data-ingestion layer. Each connector fetches raw data from its source (or reads from a fixture in mock mode) and the normalizer converts it into the standard `Event` schema. This layer is the entry point for all data flowing into the system.

### Expected Outcomes
- `backend/connectors/github_actions.py` — real connector that calls the GitHub Actions REST API and returns raw workflow run data
- `backend/connectors/kubernetes_mock.py` — mock connector that returns hard-coded pod/deployment data matching the incident fixture
- `backend/connectors/prometheus_mock.py` — mock connector that returns hard-coded metric data
- `backend/normalizer/normalizer.py` — `normalize(raw, source)` function that maps each source's raw format to an `Event`
- `tests/test_normalizer.py` — tests that feed raw connector output through the normalizer and assert the output matches the `Event` schema with correct `event_type` values

### Todo List
1. Write `backend/connectors/github_actions.py` — function `fetch_runs(repo, token)` that calls `GET /repos/{repo}/actions/runs` and returns the latest run's conclusion and steps; fall back to fixture data if no token is provided
2. Write `backend/connectors/kubernetes_mock.py` — function `fetch_pods()` that returns the mock pod list from `fixture-incident.json`-compatible data (pod name, restart count, reason)
3. Write `backend/connectors/prometheus_mock.py` — function `fetch_metrics()` that returns mock HTTP 500 rate and latency values
4. Write `backend/normalizer/normalizer.py` — implement `normalize_github_actions(raw)`, `normalize_kubernetes(raw)`, `normalize_prometheus(raw)`, each returning an `Event`; expose a top-level `normalize(raw, source: str) -> Event`
5. Write `tests/test_normalizer.py` — test each normalizer function with sample raw input and assert output fields

### Relevant Context
- Connector architecture described in `idees.pdf` §6–7 and §9
- GitHub Actions API: `GET /repos/{owner}/{repo}/actions/runs` — real endpoint, requires `Authorization: Bearer <token>`
- Kubernetes raw fields: `pod`, `restarts`, `reason` (CrashLoopBackOff)
- Prometheus raw fields: `metric`, `value`, `timestamp`
- Normalizer output must match `Event` model from Phase 1

---

## Phase 3 — Intelligence: Correlation Engine, Incident Builder, and Health Engine

**Status:** `[x] done`

### Intent
This is the core of the project. The correlation engine takes a stream of `Event` objects and applies deterministic rules to group related events into an `Incident`. The health engine then derives a per-service health status from active incidents and recent events.

### Expected Outcomes
- `backend/correlation/engine.py` — `CorrelationEngine` class with `ingest(events: list[Event]) -> list[Incident]` method
- Correlation rules implemented: same service + time window + logical chain (DEPLOY_FAILED → POD_FAILED → APPLICATION_ERROR → HIGH_ERROR_RATE)
- `backend/health/health_engine.py` — `compute_health(events, incidents) -> dict[service, status]` where status is one of `HEALTHY`, `DEGRADED`, `FAILING`, `UNKNOWN`
- `tests/test_correlation.py` — test that feeding the incident fixture events produces exactly one incident on the `backend` service
- `tests/test_health.py` — test that the healthy fixture produces all-HEALTHY map and the incident fixture produces FAILING for `backend`

### Todo List
1. Write `backend/correlation/engine.py` — define correlation rules as a list of ordered event-type chains; implement sliding time window (default 5 minutes); group events that match same service + rule chain into an `Incident`; assign `possible_cause` and `evidence` based on matched rule
2. Implement the primary rule: `[DEPLOY_FAILED, POD_FAILED, HIGH_ERROR_RATE]` on same service within 5 min → Incident with cause "Possible deployment-triggered failure"
3. Implement secondary rule: `[POD_FAILED, APPLICATION_ERROR]` → Incident with cause "Pod instability causing application errors"
4. Write `backend/health/health_engine.py` — iterate services; if service has an active `FAILING` incident → `FAILING`; if incident is `warning` severity → `DEGRADED`; if no incidents and last event is SUCCESS → `HEALTHY`; otherwise `UNKNOWN`
5. Write `tests/test_correlation.py` and `tests/test_health.py`

### Relevant Context
- Correlation logic described in `idees.pdf` §12
- Incident structure in `idees.pdf` §13
- Health states in `idees.pdf` §14
- Rules are deterministic — no AI at this phase
- Events from Phase 2 fixtures are the primary test input

---

## Phase 4 — API Layer: FastAPI Backend

**Status:** `[x] done`

### Intent
Expose the correlation and health results via a clean REST API that the frontend will consume. Wire together all backend modules: connectors → normalizer → correlation engine → health engine → API response.

### Expected Outcomes
- `backend/api/main.py` — FastAPI app with three endpoints
- `GET /graph` — returns nodes (services) with health status and edges (dependencies)
- `GET /incidents` — returns list of active incidents
- `GET /incidents/{id}` — returns a single incident with events, timeline, evidence, possible cause
- `POST /demo/{scenario}` — loads either `fixture-healthy.json` or `fixture-incident.json` to drive the demo
- CORS enabled for `http://localhost:5173`
- `tests/test_api.py` — integration tests using `httpx.AsyncClient` that call each endpoint and assert response structure

### Todo List
1. Write `backend/api/main.py` — create FastAPI app; add CORS middleware allowing `http://localhost:5173`
2. Implement in-memory store: on startup, load the healthy fixture; expose a module-level `store` with `events` and `incidents`
3. Implement `GET /graph` — call `compute_health()` on current events+incidents; build node list from known services; build edge list from fixed topology (Build→Tests→Deploy→Backend→Database); return `{nodes, edges}`
4. Implement `GET /incidents` — return current `store.incidents`
5. Implement `GET /incidents/{id}` — find incident by id; return full detail including sorted event timeline
6. Implement `POST /demo/healthy` and `POST /demo/incident` — replace store contents from corresponding fixture file; re-run correlation and health engines
7. Write `tests/test_api.py` — test all endpoints with both demo states

### Relevant Context
- API endpoints defined in `README.md` §API table
- Fixed topology: `Build → Tests → Deploy → Backend → Database` (from `idees.pdf` §15)
- CORS target is `http://localhost:5173` (frontend dev server port from README)
- In-memory store is intentional — no DB for MVP

---

## Phase 5 — Frontend: Health Map and Incident Panel

**Status:** `[ ] pending`

### Intent
Build the interactive UI using Cytoscape.js for the graph and vanilla JS for the incident panel. The frontend polls the API and updates the graph in real time. Clicking a node shows incident details.

### Expected Outcomes
- `frontend/index.html` — main page with graph canvas and incident panel
- `frontend/graph.js` — Cytoscape.js graph initialisation, node coloring by health status, polling loop, click handler
- `frontend/style.css` — dark-themed UI matching the DevOps tool aesthetic
- Clicking a node shows the incident panel with: status, events timeline, possible cause, evidence list
- Two buttons: "Load Healthy" and "Load Incident" that call `POST /demo/{scenario}` and refresh the graph
- Graph updates within 3 seconds of a demo scenario change

### Todo List
1. Write `frontend/index.html` — import Cytoscape.js from CDN; import GSAP from CDN; layout: left panel = graph, right panel = incident details sidebar
2. Write `frontend/graph.js` — `initGraph()` that calls `GET /graph` and builds Cytoscape nodes/edges; color nodes green/orange/red/grey based on health; `startPolling()` that refreshes every 3s; `onNodeClick(node)` that calls `GET /incidents` filtered by service and populates the sidebar
3. Write `frontend/style.css` — dark background, green/orange/red node color palette, clean monospace font for incident details
4. Add demo control bar with "Healthy" and "Incident" buttons that `POST /demo/healthy` or `POST /demo/incident` then force an immediate graph refresh
5. Manual test: run backend, open frontend, click "Incident" button, verify graph turns red on `backend`/`database` nodes and incident panel populates

### Relevant Context
- Frontend stack: Vanilla JS + Cytoscape.js + GSAP (`README.md` §Tech Stack)
- Node states: green = HEALTHY, orange = DEGRADED, red = FAILING, grey = UNKNOWN (`README.md` §Health Map)
- Serve frontend with `python -m http.server 5173` from the `frontend/` directory
- The graph topology is fixed: `Build → Tests → Deploy → Backend → Database`

---

## Phase 6 — AI Layer: Incident Explanation via IBM Bob

**Status:** `[ ] pending`

### Intent
Add an optional AI analyzer that takes a correlated `Incident` and generates a plain-English explanation. This uses a free LLM API (e.g. Groq `llama3-8b-8192`, OpenRouter, or Gemini free tier) to enrich the incident with a human-readable narrative. This is additive — the system works fully without it. **Build only if Phases 1–5 are complete and time permits.**

### Expected Outcomes
- `backend/ai/analyzer.py` — `explain_incident(incident: Incident) -> str` function that calls IBM Bob API with the incident's events and returns a human-readable explanation
- `GET /incidents/{id}` response includes an `explanation` field (empty string if AI is unavailable)
- The explanation is cached per incident (not re-generated on every request)
- Frontend incident panel displays the explanation block if present

### Todo List
1. Write `backend/ai/analyzer.py` — build a structured prompt from the incident (service, events timeline, evidence, possible cause); call a free LLM API (Groq / OpenRouter / Gemini) via `httpx`; parse and return the explanation string; handle API errors gracefully (return empty string, do not crash)
2. Add `explanation: str = ""` field to the `Incident` model
3. Update the correlation engine to call `explain_incident()` after creating a new incident (async, best-effort)
4. Update `GET /incidents/{id}` to include `explanation` in the response
5. Update `frontend/graph.js` incident panel to render the explanation block with a distinct style (e.g. italic, labelled "AI Analysis")
6. Test: trigger incident scenario, verify explanation text appears in the panel

### Relevant Context
- AI is explanation/enrichment only — not detection (`idees.pdf` §18)
- "Rules = detection, AI = explanation" (`idees.pdf` §18)
- Use a free-tier LLM API — Groq is recommended (free, fast, `llama3-8b-8192` model, simple OpenAI-compatible API)
- Add `GROQ_API_KEY` (or equivalent) to a `.env` file; load with `python-dotenv`
- Graceful degradation is required: if no API key or service is unavailable, skip silently

---

## Phase 7 — Demo Polish and Final Wiring

**Status:** `[ ] pending`

### Intent
Prepare the two demo scenarios for live presentation. Verify the full end-to-end flow works. Add any missing labels, animations, or UX touches that make the demo clear to a jury. Write the final README section for quick start.

### Expected Outcomes
- Full end-to-end flow works: click "Incident" → graph turns red → incident panel shows full chain → AI explanation visible
- Full end-to-end flow works: click "Healthy" → all nodes green → no incidents shown
- `README.md` updated with accurate Quick Start instructions
- No Python exceptions during either demo scenario
- Demo can be run by anyone with `pip install -r requirements.txt` + `uvicorn api.main:app`

### Todo List
1. Run full `pytest tests/` suite — fix any failing tests
2. Run both demo scenarios end-to-end: healthy → incident → healthy, verify no regressions
3. Add GSAP pulse animation on newly-failed nodes when switching to incident scenario
4. Add a "Last updated" timestamp to the frontend so it's clear the graph is live
5. Verify `README.md` Quick Start matches actual startup commands
6. Prepare the two-sentence pitch for the demo: "Argus is an intelligent DevOps correlation layer. It takes four unrelated alerts and tells you: these are one incident, here's why."

### Relevant Context
- Demo scenarios defined in `idees.pdf` §21 (Phase 5 — Démo)
- The pitch phrase: `idees.pdf` §22
- GSAP is already included in the tech stack for animation

---

## Architecture Summary

```
Connectors (GitHub Actions / K8s mock / Prometheus mock)
    ↓
Normalizer  →  Event[]
    ↓
Correlation Engine  →  Incident[]
    ↓
Health Engine  →  {service: status}
    ↓
FastAPI  →  GET /graph, GET /incidents, POST /demo
    ↓
Cytoscape.js Frontend  →  Health Map + Incident Panel
    ↓ (optional)
IBM Bob AI  →  Plain-English Explanation
```

## Dependency Order

Phase 1 must complete before any other phase.
Phase 2 depends on Phase 1 (uses Event model).
Phase 3 depends on Phase 1 + 2 (uses Event + Incident models and normalizer output).
Phase 4 depends on Phase 1–3 (wires all modules into the API).
Phase 5 depends on Phase 4 (consumes the API).
Phase 6 depends on Phase 3 + 4 (enriches Incident after correlation).
Phase 7 depends on all previous phases.
