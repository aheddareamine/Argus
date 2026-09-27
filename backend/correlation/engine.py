"""
Correlation Engine — groups related Events into Incidents using deterministic rules.

Rules are defined as ordered chains of event types that must:
  1. Involve overlapping services (the triggering service or its downstream)
  2. Fall within a configurable time window (default 5 minutes)
  3. Match the logical chain order (not necessarily strict sequence — subset match)

Design:
  - Rules are data, not code — easy to extend without touching engine logic
  - One pass over the event list per rule
  - An event can only belong to one incident (first matching rule wins)
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set

from backend.models.event import Event
from backend.models.incident import Incident


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

class CorrelationRule:
    """
    A named rule that describes a causal chain of event types.

    Attributes:
        name:           Human-readable rule identifier.
        chain:          Ordered list of event_type strings that must all appear.
        services:       Set of service names this rule applies to. Empty = any service.
        window_seconds: Maximum seconds between first and last event in the chain.
        possible_cause: Text assigned to matched incidents.
        severity:       "critical" or "warning".
        cross_service:  If True, events from different services in the chain are
                        allowed (e.g. deploy → backend → database).
    """
    def __init__(
        self,
        name: str,
        chain: List[str],
        possible_cause: str,
        severity: str = "critical",
        window_seconds: int = 300,
        services: Optional[Set[str]] = None,
        cross_service: bool = False,
    ):
        self.name = name
        self.chain = chain
        self.possible_cause = possible_cause
        self.severity = severity
        self.window_seconds = window_seconds
        self.services = services or set()
        self.cross_service = cross_service


# Primary rules — ordered from most specific to least specific
RULES: List[CorrelationRule] = [
    CorrelationRule(
        name="deployment_cascade_failure",
        chain=["DEPLOY_FAILED", "POD_FAILED", "HIGH_ERROR_RATE"],
        possible_cause=(
            "Deployment failure triggered a pod crash, causing elevated HTTP error rates. "
            "Likely root cause: misconfiguration or bad artifact in the deployment."
        ),
        severity="critical",
        window_seconds=300,
        cross_service=True,
    ),
    CorrelationRule(
        name="deployment_db_cascade",
        chain=["DEPLOY_FAILED", "POD_FAILED", "DATABASE_CONNECTION_ERROR", "HIGH_ERROR_RATE"],
        possible_cause=(
            "Deployment failure led to pod instability and database connectivity loss, "
            "resulting in high HTTP error rates. Possible database connectivity issue."
        ),
        severity="critical",
        window_seconds=300,
        cross_service=True,
    ),
    CorrelationRule(
        name="pod_app_error",
        chain=["POD_FAILED", "APPLICATION_ERROR"],
        possible_cause=(
            "Pod instability is causing repeated application errors. "
            "Check container logs and resource limits."
        ),
        severity="critical",
        window_seconds=300,
        cross_service=False,
    ),
    CorrelationRule(
        name="pod_db_error",
        chain=["POD_FAILED", "DATABASE_CONNECTION_ERROR"],
        possible_cause=(
            "Pod failure is accompanied by database connection errors. "
            "The database may be unreachable or the connection string is incorrect."
        ),
        severity="critical",
        window_seconds=300,
        cross_service=True,
    ),
    CorrelationRule(
        name="high_error_rate_standalone",
        chain=["APPLICATION_ERROR", "HIGH_ERROR_RATE"],
        possible_cause=(
            "Application errors are causing an elevated HTTP 500 rate. "
            "Review recent deployments and application logs."
        ),
        severity="warning",
        window_seconds=300,
        cross_service=False,
    ),
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CorrelationEngine:
    """
    Ingests a list of Events and produces a list of Incidents.

    Usage:
        engine = CorrelationEngine()
        incidents = engine.ingest(events)
    """

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, events: List[Event]) -> List[Incident]:
        """
        Run all correlation rules over the event list.

        Returns a deduplicated list of Incidents. Events are consumed by the
        first matching rule; they cannot appear in two incidents.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        used_ids: Set[str] = set()
        incidents: List[Incident] = []

        for rule in RULES:
            matched = self._apply_rule(rule, sorted_events, used_ids)
            for incident in matched:
                for ev in incident.events:
                    used_ids.add(ev.id)
                incidents.append(incident)

        return incidents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_rule(
        self,
        rule: CorrelationRule,
        events: List[Event],
        used_ids: Set[str],
    ) -> List[Incident]:
        """
        Slide a window over the sorted event list and look for the rule's chain.

        Returns a list of Incidents (may be empty).
        """
        incidents: List[Incident] = []
        available = [e for e in events if e.id not in used_ids]

        # Group events by their relevant "key"
        # For cross_service rules the key is a group of services that can appear
        # together.  For single-service rules the key is the service name.
        if rule.cross_service:
            groups = self._group_cross_service(available)
        else:
            groups = self._group_by_service(available)

        for group_events in groups.values():
            incident = self._match_chain(rule, group_events)
            if incident:
                incidents.append(incident)

        return incidents

    def _group_by_service(self, events: List[Event]) -> Dict[str, List[Event]]:
        """Group events by service name."""
        groups: Dict[str, List[Event]] = {}
        for ev in events:
            groups.setdefault(ev.service, []).append(ev)
        return groups

    def _group_cross_service(self, events: List[Event]) -> Dict[str, List[Event]]:
        """
        For cross-service rules, group events into a single pool keyed by
        the primary triggering service (deploy/build/tests).  This lets a
        DEPLOY_FAILED on 'deploy' combine with a POD_FAILED on 'backend'.
        """
        # All events go into one cross-service pool
        return {"_cross": events}

    def _match_chain(
        self,
        rule: CorrelationRule,
        events: List[Event],
    ) -> Optional[Incident]:
        """
        Try to find all event types in rule.chain within the time window.

        Strategy: find the first event matching chain[0], then check that
        all remaining chain event types appear within window_seconds of it.
        If matched, build and return an Incident.
        """
        chain_set = set(rule.chain)
        window = timedelta(seconds=rule.window_seconds)

        for i, anchor in enumerate(events):
            if anchor.event_type != rule.chain[0]:
                continue

            # Collect candidates within the window
            window_events = [
                e for e in events[i:]
                if e.timestamp - anchor.timestamp <= window
                and e.timestamp >= anchor.timestamp
            ]

            # Check all chain types are present
            present_types = {e.event_type for e in window_events}
            if not chain_set.issubset(present_types):
                continue

            # Pick the best representative event for each chain type
            matched_events: List[Event] = []
            seen_types: Set[str] = set()
            for chain_type in rule.chain:
                for ev in window_events:
                    if ev.event_type == chain_type and chain_type not in seen_types:
                        matched_events.append(ev)
                        seen_types.add(chain_type)
                        break

            # Determine primary service (service of the first matched event)
            primary_service = matched_events[0].service

            # Build evidence list
            evidence = self._build_evidence(matched_events)

            incident = Incident(
                id=f"inc-{uuid.uuid4().hex[:8]}",
                service=primary_service,
                severity=rule.severity,  # type: ignore[arg-type]
                status="active",
                start_time=matched_events[0].timestamp,
                events=sorted(matched_events, key=lambda e: e.timestamp),
                possible_cause=rule.possible_cause,
                evidence=evidence,
            )
            return incident

        return None

    def _build_evidence(self, events: List[Event]) -> List[str]:
        """Build a human-readable evidence list from matched events."""
        _labels: Dict[str, str] = {
            "DEPLOY_FAILED": "Deployment failed",
            "BUILD_FAILED": "Build failed",
            "TEST_FAILED": "Tests failed",
            "POD_FAILED": "Pod crashed (CrashLoopBackOff)",
            "POD_RESTARTED": "Pod restarted repeatedly",
            "APPLICATION_ERROR": "Application errors detected in logs",
            "DATABASE_CONNECTION_ERROR": "Database connection refused",
            "HIGH_ERROR_RATE": "HTTP 500 error rate elevated",
            "HIGH_LATENCY": "Response latency elevated",
            "HIGH_CPU": "CPU usage exceeded threshold",
            "HIGH_MEMORY": "Memory usage exceeded threshold",
        }
        seen: Set[str] = set()
        evidence: List[str] = []
        for ev in sorted(events, key=lambda e: e.timestamp):
            label = _labels.get(ev.event_type, ev.event_type)
            if label not in seen:
                evidence.append(label)
                seen.add(label)
        return evidence
