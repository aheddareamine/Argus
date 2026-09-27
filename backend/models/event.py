from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


EventType = Literal[
    "BUILD_SUCCESS",
    "BUILD_FAILED",
    "TEST_SUCCESS",
    "TEST_FAILED",
    "DEPLOY_SUCCESS",
    "DEPLOY_FAILED",
    "POD_STARTED",
    "POD_FAILED",
    "POD_RESTARTED",
    "APPLICATION_ERROR",
    "DATABASE_CONNECTION_ERROR",
    "HIGH_CPU",
    "HIGH_MEMORY",
    "HIGH_ERROR_RATE",
    "HIGH_LATENCY",
]

StatusType = Literal["ok", "warning", "critical", "info"]


class Event(BaseModel):
    id: str
    timestamp: datetime
    source: str  # e.g. "github_actions", "kubernetes", "prometheus"
    service: str  # e.g. "backend", "database", "build"
    event_type: EventType
    status: StatusType
    details: Dict[str, Any] = Field(default_factory=dict)
