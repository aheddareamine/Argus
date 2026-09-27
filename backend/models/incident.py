from __future__ import annotations

from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field

from .event import Event


SeverityType = Literal["warning", "critical"]
IncidentStatus = Literal["active", "resolved"]


class Incident(BaseModel):
    id: str
    service: str
    severity: SeverityType
    status: IncidentStatus = "active"
    start_time: datetime
    events: List[Event] = Field(default_factory=list)
    possible_cause: str = ""
    evidence: List[str] = Field(default_factory=list)
    explanation: str = ""  # populated by AI layer if available
