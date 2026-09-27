"""
In-memory store — shared application state.

All modules import from here so the API, demo switcher, and correlation
engine all read/write the same object.
"""
from __future__ import annotations

import json
import pathlib
from typing import List

from backend.models.event import Event
from backend.models.incident import Incident

_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


class Store:
    def __init__(self) -> None:
        self.events: List[Event] = []
        self.incidents: List[Incident] = []
        self.scenario: str = "healthy"

    def load_fixture(self, scenario: str) -> None:
        """Replace store contents from a fixture file and re-run the pipeline."""
        filename = f"fixture-{scenario}.json"
        path = _FIXTURES_DIR / filename
        with open(path) as f:
            raw = json.load(f)

        from backend.correlation.engine import CorrelationEngine

        self.events = [Event(**e) for e in raw]
        self.incidents = CorrelationEngine().ingest(self.events)
        self.scenario = scenario


# Module-level singleton — imported by main.py and tests
store = Store()
