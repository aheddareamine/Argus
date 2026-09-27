<p align="center">
  <img src="./assets/logo.png" alt="Project Argus Logo" width="450">
</p>

<p align="center">
  <em>Built for the lablab.ai "Back for Another Hack: Meet IBM Bob 2.0" Hackathon</em>
</p>
# Project Argus

A live DevOps health graph that brings alerts, logs, traces, and events from different tools into one view. Instead of checking each system separately, Argus shows how failures are connected and how an incident moves through the pipeline.

## 🚀 Quick Start

### Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt

# Run from the project root (not from backend/)
cd ..
uvicorn backend.api.main:app --reload --port 8090
```

### Frontend

```bash
cd frontend
python -m http.server 5173
```

Open the frontend at `http://localhost:5173`.

## 🎯 How It Works

Argus collects events from different parts of the DevOps environment and converts them into a common format.

The correlation engine then looks for related events and groups them into incidents.

For example:

```text
Deploy failed
     ↓
Service failed
     ↓
Database connection error
     ↓
HTTP 500 rate increased
```

Instead of showing these as four separate alerts, Argus displays them as one incident with the related events and evidence.

## 📊 Health Map

The main interface is a live graph showing the current state of the system.

* Green nodes are healthy
* Warning nodes indicate degraded services
* Red nodes indicate failures
* Connections show relationships between components
* Clicking a node displays related incident information

The graph updates as new events are received.

## ✅ Features

* **Live Health Graph** - View the state of the pipeline and its services in one place
* **Event Correlation** - Group related failures into a single incident
* **Failure Chains** - See how a failure propagates through dependent components
* **Incident Details** - View the events, timeline, and evidence behind an incident
* **Multiple Connectors** - Designed to receive events from different DevOps and monitoring tools
* **Event Normalization** - Convert different event formats into a common schema
* **Rule-Based Detection** - Detect incidents using deterministic correlation rules
* **Interactive Graph** - Explore services and their relationships directly from the UI
* **AI Explanations** - Optional AI layer for explaining detected incidents in plain English

## 📁 Project Structure

```text
backend/
├── connectors/
│   ├── github_actions.py
│   ├── kubernetes_mock.py
│   └── prometheus_mock.py
├── models/
│   ├── event.py
│   └── incident.py
├── normalizer/
│   └── normalizer.py
├── correlation/
│   └── engine.py
├── health/
│   └── health_engine.py
├── fixtures/
│   ├── fixture-healthy.json
│   └── fixture-incident.json
└── api/
    └── main.py

frontend/
├── index.html
├── graph.js
└── style.css

tests/
```

## 🔌 Event Types

The MVP currently supports events such as:

```text
BUILD_SUCCESS / BUILD_FAILED
TEST_SUCCESS / TEST_FAILED
DEPLOY_SUCCESS / DEPLOY_FAILED
POD_STARTED / POD_FAILED / POD_RESTARTED
APPLICATION_ERROR
HIGH_ERROR_RATE
```

Events follow a common schema:

```json
{
  "id": "evt-001",
  "timestamp": "2026-09-25T14:22:00",
  "source": "kubernetes",
  "service": "backend",
  "event_type": "POD_FAILED",
  "status": "critical",
  "details": {
    "pod": "backend-7d8f",
    "restarts": 8,
    "reason": "CrashLoopBackOff"
  }
}
```

## 🔗 API

| Endpoint              | Description                                   |
| --------------------- | --------------------------------------------- |
| `GET /graph`          | Current nodes, connections, and health status |
| `GET /incidents`      | Active incidents                              |
| `GET /incidents/{id}` | Incident details and evidence                 |

## 🧪 Demo

### Healthy

```text
Build → Tests → Deploy → Backend → Database
  🟢      🟢       🟢        🟢         🟢
```

### Incident

```text
Deploy 🔴
    ↓
Backend 🔴
    ↓
Database 🔴
    ↓
HTTP 500 🔴
```

The incident panel shows the events that were detected and the timeline connecting them.

## 🛠️ Tech Stack

**Backend**

* Python
* FastAPI
* Pydantic
* Uvicorn

**Frontend**

* Vanilla JavaScript
* Cytoscape.js
* GSAP

The MVP uses an in-memory store, so no database is required to run the demo.

## 🚧 Current Scope

The current version uses rule-based correlation with one real connector and mocked connectors for the remaining integrations.

The graph currently uses a fixed topology. The connector architecture is designed so that additional tools and event sources can be added later without changing the core correlation engine.

## 🗺️ Roadmap

* Add more integrations
* Support dynamic service dependencies
* Add logs and traces as correlation sources
* Store historical incidents
* Add more advanced correlation rules
* Add AI-powered incident explanations
* Add natural language investigation

---

Built for the **lablab.ai "Back for Another Hack: Meet IBM Bob 2.0" Hackathon**.
