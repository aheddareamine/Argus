#!/usr/bin/env bash
cd /home/ouimaison/Desktop/LabLab_ai/Argus
source backend/venv/bin/activate

export PYTHONPATH=/home/ouimaison/Desktop/LabLab_ai/Argus
PORT=8765
uvicorn backend.api.main:app --port $PORT --log-level error &
SERVER_PID=$!
sleep 3

echo "=== /health ==="
curl -s http://localhost:$PORT/health

echo ""
echo "=== POST /demo/incident ==="
curl -s -X POST http://localhost:$PORT/demo/incident > /tmp/argus_demo.json
python3 << 'PYEOF'
import json
d = json.load(open("/tmp/argus_demo.json"))
failing = [n["id"] for n in d["nodes"] if n["health"] == "FAILING"]
print("Scenario:", d["scenario"])
print("Failing nodes:", failing)
print("Incident count:", d["incident_count"])
PYEOF

echo ""
echo "=== GET /incidents ==="
curl -s http://localhost:$PORT/incidents > /tmp/argus_incs.json
python3 << 'PYEOF'
import json
d = json.load(open("/tmp/argus_incs.json"))
inc = d[0]
print("ID:", inc["id"])
print("Service:", inc["service"])
print("Severity:", inc["severity"])
print("Cause:", inc["possible_cause"][:80])
print("Evidence:", inc["evidence"])
print("Event count:", len(inc["events"]))
PYEOF

echo ""
echo "=== POST /demo/healthy (reset) ==="
curl -s -X POST http://localhost:$PORT/demo/healthy > /tmp/argus_healthy.json
python3 << 'PYEOF'
import json
d = json.load(open("/tmp/argus_healthy.json"))
failing = [n["id"] for n in d["nodes"] if n["health"] == "FAILING"]
print("Scenario:", d["scenario"])
print("Failing nodes:", failing)
print("Incident count:", d["incident_count"])
PYEOF

kill $SERVER_PID 2>/dev/null
echo ""
echo "Server stopped. Smoke test complete."
