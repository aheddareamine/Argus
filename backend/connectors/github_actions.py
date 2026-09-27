"""
GitHub Actions connector.

Real connector that calls the GitHub Actions REST API.
Falls back to mock data (from fixture-incident.json) if GITHUB_TOKEN is not set
or if ARGUS_MOCK_GITHUB=true is set in the environment.
"""
from __future__ import annotations

import os
import pathlib
import json
from typing import Any, Dict, List

import httpx

_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


def _mock_runs() -> List[Dict[str, Any]]:
    """Return raw mock GitHub Actions data shaped like the real API response."""
    return [
        {
            "id": "10042",
            "name": "CI/CD Pipeline",
            "head_branch": "main",
            "head_sha": "deadbeef1234",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-09-25T14:18:00Z",
            "updated_at": "2026-09-25T14:20:00Z",
            "jobs": [
                {"name": "build", "conclusion": "success"},
                {"name": "test", "conclusion": "success"},
                {"name": "deploy", "conclusion": "failure"},
            ],
        }
    ]


def _mock_runs_healthy() -> List[Dict[str, Any]]:
    return [
        {
            "id": "10001",
            "name": "CI/CD Pipeline",
            "head_branch": "main",
            "head_sha": "abc1234",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-09-25T13:58:00Z",
            "updated_at": "2026-09-25T14:05:00Z",
            "jobs": [
                {"name": "build", "conclusion": "success"},
                {"name": "test", "conclusion": "success"},
                {"name": "deploy", "conclusion": "success"},
            ],
        }
    ]


def fetch_runs(
    repo: str,
    token: str | None = None,
    per_page: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fetch the latest workflow runs for a GitHub repository.

    Args:
        repo:     "owner/repo" format, e.g. "my-org/my-app"
        token:    GitHub personal access token. If None, reads GITHUB_TOKEN env var. 
        per_page: number of runs to return (default 5)

    Returns:
        List of raw workflow run dicts (GitHub API shape).
        Falls back to mock data if token is unavailable or
        ARGUS_MOCK_GITHUB=true is set.
    """
    use_mock = os.getenv("ARGUS_MOCK_GITHUB", "false").lower() == "true"
    if use_mock:
        return _mock_runs()

    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if not resolved_token:
        # No token — return mock so the rest of the pipeline still works
        return _mock_runs()

    url = f"https://api.github.com/repos/{repo}/actions/runs"
    headers = {
        "Authorization": f"Bearer {resolved_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"per_page": per_page, "branch": "main"}

    with httpx.Client(timeout=10) as client:
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("workflow_runs", [])
