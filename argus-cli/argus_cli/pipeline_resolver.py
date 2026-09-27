"""
Pipeline resolver.

Takes detected components and produces an ordered stage list + component mapping
using a fixed stage-weight table:

  build(0) → test(1) → deploy(2) → container(3) → orchestration(4) → observability(5)

Components with no clear stage default to appearing after deploy (weight 2.5).
"""
from __future__ import annotations

from typing import Any, Dict, List

from argus_cli.models import DetectedComponent

# Stage weights — lower = earlier in the pipeline
STAGE_WEIGHTS: Dict[str, int] = {
    "build":         0,
    "test":          1,
    "deploy":        2,
    "container":     3,
    "orchestration": 4,
    "observability": 5,
}

# Icon keys used by the frontend to select SVG/emoji icons
STAGE_ICONS: Dict[str, str] = {
    "build":         "github",
    "test":          "test",
    "deploy":        "deploy",
    "container":     "docker",
    "orchestration": "kubernetes",
    "observability": "prometheus",
}

# Human-readable stage labels
STAGE_LABELS: Dict[str, str] = {
    "build":         "Build",
    "test":          "Test",
    "deploy":        "Deploy",
    "container":     "Container",
    "orchestration": "Orchestration",
    "observability": "Observability",
}


def resolve(
    components: List[DetectedComponent],
    project_id: str = "default",
) -> Dict[str, Any]:
    """
    Build the full pipeline description from a list of detected components.

    Returns a dict matching the GET /pipeline/{project_id} response schema:
    {
        "project_id": str,
        "stages": [
            {
                "id": str,           # e.g. "build"
                "label": str,        # e.g. "Build"
                "weight": int,       # 0–5
                "icon": str,         # frontend icon key
                "connector": str,    # e.g. "github_actions"
                "services": [str],   # service names
                "status": str,       # "healthy" | "failing" | "unknown"
            }, ...
        ],
        "edges": [
            {"source": str, "target": str}, ...
        ],
        "nodes": [
            {
                "id": str,           # service name
                "label": str,
                "stage": str,        # stage id this node belongs to
                "connector": str,    # connector type
                "health": str,       # "HEALTHY" | "FAILING" | "UNKNOWN" (uppercase for frontend)
            }, ...
        ]
    }
    """
    # Sort components by stage weight, unknown stages come after deploy
    def weight(c: DetectedComponent) -> float:
        return STAGE_WEIGHTS.get(c.stage, 2.5)

    sorted_components = sorted(components, key=weight)

    stages = []
    all_nodes = []
    seen_services: set = set()

    for comp in sorted_components:
        stage_id = comp.stage
        stage_weight = STAGE_WEIGHTS.get(stage_id, 3)

        stages.append({
            "id": stage_id,
            "label": STAGE_LABELS.get(stage_id, stage_id.capitalize()),
            "weight": stage_weight,
            "icon": STAGE_ICONS.get(stage_id, "generic"),
            "connector": comp.connector,
            "services": comp.services,
            "status": comp.status,
        })

        health_map = {"healthy": "HEALTHY", "failing": "FAILING", "unknown": "UNKNOWN"}
        for svc in comp.services:
            if svc not in seen_services:
                seen_services.add(svc)
                all_nodes.append({
                    "id": svc,
                    "label": svc.replace("-", " ").replace("_", " ").capitalize(),
                    "stage": stage_id,
                    "connector": comp.connector,
                    "health": health_map.get(comp.status, "UNKNOWN"),
                })

    # Build edges: connect each stage's services to the next stage's services
    edges = []
    for i in range(len(stages) - 1):
        src_services = stages[i]["services"]
        tgt_services = stages[i + 1]["services"]
        for src in src_services:
            for tgt in tgt_services:
                edges.append({"source": src, "target": tgt})

    return {
        "project_id": project_id,
        "stages": stages,
        "edges": edges,
        "nodes": all_nodes,
    }
