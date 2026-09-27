<p align="center">
  <img src="./assets/logo.png" alt="Project Argus Logo" width="450">
</p>

<p align="center">
  <em>Built for the lablab.ai "Back for Another Hack: Meet IBM Bob 2.0" Hackathon</em>
</p>

# Project Argus

**Argus** is a live DevOps health map and incident intelligence dashboard. It aggregates alerts, logs, traces, and events from different tools into a single, unified view. Instead of debugging systems in isolation, Argus visualizes how failures are connected and how incidents propagate through your pipeline in real-time.

## 🚀 Quick Start

The project consists of a Python FastAPI backend and a modern Next.js frontend.

### 1. Backend Setup

The backend serves the graph topology, correlation engine, and incident states on port `8090`.

```bash
# 1. Create a virtual environment
cd backend
python -m venv venv

# 2. Activate it
# Linux / macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the API (from the project root)
cd ..
uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload
```

### 2. Frontend Setup

The frontend is a modern Next.js application located in the `final_front_end` directory.

```bash
# Open a new terminal instance
cd final_front_end

# Install dependencies (using pnpm)
pnpm install

# Start the development server
pnpm dev -p 3000
```

Open your browser to `http://localhost:3000` to view the dashboard!

## 🧪 Interactive Demo Features

Argus includes built-in demo endpoints to simulate real-time incidents and resolutions right on the dashboard:

- **Simulate Failure**: Click the `SIMULATE FAILURE` button in the top tools menu to instantly mock a cascading failure across the deployment pipeline. The graph will immediately reflect the degraded health.
- **View Logs**: Click `VIEW LOGS` on an active incident to open a raw terminal-style modal displaying chronological event traces and root cause metadata.
- **Open Runbook**: Click `OPEN RUNBOOK` to view remediation steps. You can click `RESOLVE INCIDENT` inside the runbook to mark the system healthy again.
- **Light/Dark Mode**: Seamlessly toggle themes using the Moon/Sun icon in the top right.
- **Mock Settings**: Click the gear icon to view mocked AI auto-remediation toggles designed for the IBM Bob integration.

## 🎯 How It Works

Argus collects events from across the DevOps environment (e.g., CI/CD, Kubernetes, databases) and normalizes them into a common format. 

The deterministic **Correlation Engine** groups related events into a single "Incident".

```text
Deploy failed
     ↓
Service failed
     ↓
Database connection error
     ↓
HTTP 500 rate increased
```

Instead of drowning in separate alerts, Argus presents a single incident containing all related evidence and a chronological timeline.

## ✅ Features

* **Live Health Graph**: Real-time visualization of the pipeline topology using React Flow and custom SVGs.
* **Event Correlation**: Group failures into single incidents.
* **Failure Chains**: See dependency propagation.
* **Interactive UI**: Shadcn/ui dialogs, dynamic SVGs, and responsive design.
* **Event Normalization**: Unified schema for disparate tools.
* **IBM Bob Integration**: Designed to support AI-powered incident explanations and auto-remediation (mocked in UI).

## 🛠️ Tech Stack

### Backend
* **Python 3**
* **FastAPI** (REST API & WebSockets)
* **Pydantic**
* **Uvicorn**

### Frontend
* **Next.js 16** (App Router)
* **React**
* **Tailwind CSS**
* **Shadcn/ui** (Radix Primitives)
* **Lucide Icons**
* **Next-Themes**

## 🔗 API Reference

| Endpoint              | Method | Description                                   |
| --------------------- | ------ | --------------------------------------------- |
| `GET /graph`          | GET    | Current nodes, connections, and health status |
| `GET /incidents`      | GET    | Active incidents                              |
| `POST /demo/incident` | POST   | Triggers a simulated cascading incident       |
| `POST /demo/healthy`  | POST   | Resolves active incidents                     |

## 🗺️ Roadmap

- [ ] Complete live IBM Bob integration for natural language investigation.
- [ ] Add dynamic service dependency mapping.
- [ ] Incorporate distributed tracing (OpenTelemetry).
- [ ] Persist historical incidents to a Postgres database.

---
*Built for the **lablab.ai "Back for Another Hack: Meet IBM Bob 2.0" Hackathon**.*
