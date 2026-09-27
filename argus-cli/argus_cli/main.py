"""
Argus CLI — entry point.

Usage:
    argus start [PATH] [--backend http://localhost:8000] [--interval 5] [--simulate-incident]
    argus init  [PATH]

argus start:
    Detects DevOps tools in PATH (default: cwd), pushes events to the
    Argus backend every N seconds, and opens the frontend in a browser.

argus init:
    Guided wizard to write a .env file for GITHUB_TOKEN / GITHUB_REPO.
"""
from __future__ import annotations

import os
import pathlib
import sys
import time
import json
import webbrowser
import subprocess
import signal
from typing import List, Optional

import httpx

from argus_cli.models import DetectedComponent
from argus_cli.detectors import (
    detect_github_actions,
    detect_docker,
    detect_test_runner,
    detect_kubernetes,
    detect_prometheus,
)
from argus_cli.pipeline_resolver import resolve


# ── Helpers ────────────────────────────────────────────────────────────────────



import socket
import urllib.request
import urllib.error
import urllib.parse

def _is_argus_backend(port: int) -> bool:
    try:
        req = urllib.request.Request(f"http://localhost:{port}/incidents", method="GET")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

def _spawn_backend_if_needed(project_root: pathlib.Path) -> str:
    port = 8000
    if _is_argus_backend(port):
        return f"http://localhost:{port}"
    
    port = 8090
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                break
        if _is_argus_backend(port):
            return f"http://localhost:{port}"
        port += 1

    print(f"Spawning backend on port {port}...")
    
    repo_root = project_root.parent if project_root.name == "demo-project" else project_root
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    log_file = open(repo_root / "backend.log", "a")
    
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--port", str(port)],
        cwd=str(repo_root),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    
    time.sleep(2)
    return f"http://localhost:{port}"
    
    port = 8090
    print(f"Spawning backend on port {port}...")
    
    # We assume backend is in the same repo as argus-cli for this hackathon
    repo_root = project_root.parent if project_root.name == "demo-project" else project_root
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    log_file = open(repo_root / "backend.log", "a")
    
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--port", str(port)],
        cwd=str(repo_root),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    
    # Wait a bit for it to start
    time.sleep(2)
    return f"http://localhost:{port}"

def _load_dotenv(path: pathlib.Path) -> None:
    """Load a .env file from the project root into os.environ."""
    env_file = path / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _detect_all(
    project_root: pathlib.Path,
    simulate_incident: bool = False,
) -> List[DetectedComponent]:
    """Run all detectors and return non-None results."""
    components: List[DetectedComponent] = []
    for detector, kwargs in [
        (detect_github_actions, {}),
        (detect_test_runner,    {}),
        (detect_docker,         {}),
        (detect_kubernetes,     {"simulate_incident": simulate_incident}),
        (detect_prometheus,     {"simulate_incident": simulate_incident}),
    ]:
        try:
            result = detector(project_root, **kwargs)  # type: ignore[call-arg]
            if result is not None:
                components.append(result)
        except TypeError:
            # detector doesn't accept extra kwargs
            try:
                result = detector(project_root)  # type: ignore[call-arg]
                if result is not None:
                    components.append(result)
            except Exception as exc:
                print(f"  [warn] detector {detector.__module__} failed: {exc}")
        except Exception as exc:
            print(f"  [warn] detector {detector.__module__} failed: {exc}")
    return components


def _push_to_backend(
    components: List[DetectedComponent],
    backend: str,
    project_id: str,
) -> bool:
    """POST detected component events to the backend /ingest endpoint."""
    pipeline = resolve(components, project_id)

    payload = {
        "project_id": project_id,
        "pipeline": pipeline,
        "components": [
            {
                "name": c.name,
                "connector": c.connector,
                "stage": c.stage,
                "status": c.status,
                "services": c.services,
                "raw_events": c.raw_events,
                "meta": c.meta,
            }
            for c in components
        ],
    }

    try:
        with httpx.Client(timeout=8) as client:
            resp = client.post(f"{backend}/ingest", json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        print(f"  [warn] backend push failed: {exc}")
        return False


def _print_detection_summary(components: List[DetectedComponent]) -> None:
    if not components:
        print("  ⚠  No DevOps tools detected. Is this the right directory?")
        return
    for comp in components:
        icon = {"healthy": "✓", "failing": "✕", "unknown": "○"}.get(comp.status, "○")
        print(f"  {icon}  {comp.name:25s} [{comp.stage}]  services: {', '.join(comp.services)}")


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_init(project_root: pathlib.Path) -> None:
    """Interactive wizard to write .env."""
    print("\n◈  Argus init\n")
    env_path = project_root / ".env"

    token = input("GitHub personal access token (leave blank to skip): ").strip()
    repo  = input("GitHub repo (owner/repo, leave blank to skip): ").strip()

    lines = []
    if token:
        lines.append(f'GITHUB_TOKEN={token}')
    if repo:
        lines.append(f'GITHUB_REPO={repo}')

    if lines:
        existing = env_path.read_text() if env_path.exists() else ""
        with env_path.open("a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n".join(lines) + "\n")
        print(f"\n✓  Written to {env_path}")
    else:
        print("\n(nothing written)")


def cmd_start(
    project_root: pathlib.Path,
    backend: str = "http://localhost:8000",
    interval: int = 5,
    simulate_incident: bool = False,
    open_browser: bool = True,
    project_id: str = "default",
) -> None:
    """
    Main watch loop:
    1. Load .env from project root
    2. Detect tools
    3. Push to backend
    4. Sleep interval seconds
    5. Repeat until Ctrl-C
    """
    _load_dotenv(project_root)

    print(f"\n◈  Argus — watching {project_root}")
    if simulate_incident:
        print("   ⚡ Incident simulation is ON — mocked connectors will emit failure events")
    print(f"   Backend : {backend}")
    print(f"   Interval: {interval}s")
    print(f"   Press Ctrl-C to stop\n")

    # Spawn backend if needed
    if backend == "http://localhost:8000":
        backend = _spawn_backend_if_needed(project_root)
        print(f"   Using Backend : {backend}")

    # Initial detection
    print("Detecting tools...")
    components = _detect_all(project_root, simulate_incident)
    _print_detection_summary(components)

    if not components:
        print("\nNo tools detected — exiting.")
        return

    # Push initial pipeline config
    print("\nPushing to backend...")
    ok = _push_to_backend(components, backend, project_id)
    if ok:
        print("  ✓  Backend updated")
    else:
        print(f"  ✕  Could not reach backend at {backend}")
        print("     Start the backend first:  uvicorn backend.api.main:app --reload --port 8000")

    frontend_url = backend
    print(f"\n🔗 OPEN THE UI HERE: {frontend_url}\n")
    if open_browser:
        try:
            webbrowser.open(frontend_url)
        except Exception:
            pass

    print("\nWatching for changes...\n")

    # Watch loop
    def handle_interrupt(sig, frame):  # type: ignore[no-untyped-def]
        print("\n\n◈  Argus stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    last_components_repr = repr(components)

    while True:
        time.sleep(interval)
        new_components = _detect_all(project_root, simulate_incident)
        new_repr = repr(new_components)

        if new_repr != last_components_repr:
            print("  ↺  Change detected — re-pushing...")
            _push_to_backend(new_components, backend, project_id)
            last_components_repr = new_repr
        else:
            # Still push on every cycle so the graph stays live
            _push_to_backend(new_components, backend, project_id)


# ── CLI parser (no external deps — pure argparse) ────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="argus",
        description="Argus — DevOps Health Map CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # argus start
    p_start = sub.add_parser("start", help="Start watching a project")
    p_start.add_argument("path", nargs="?", default=".", help="Project root (default: cwd)")
    p_start.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    p_start.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    p_start.add_argument("--simulate-incident", action="store_true",
                         help="Force mocked connectors to emit incident events")
    p_start.add_argument("--no-browser", action="store_true", help="Don't open browser")
    p_start.add_argument("--project-id", default="default", help="Project identifier")

    # argus init
    p_init = sub.add_parser("init", help="Initialize .env in a project")
    p_init.add_argument("path", nargs="?", default=".", help="Project root (default: cwd)")

    args = parser.parse_args()

    if args.command == "start":
        project_root = pathlib.Path(args.path).resolve()
        cmd_start(
            project_root=project_root,
            backend=args.backend,
            interval=args.interval,
            simulate_incident=args.simulate_incident,
            open_browser=not args.no_browser,
            project_id=args.project_id,
        )
    elif args.command == "init":
        project_root = pathlib.Path(args.path).resolve()
        cmd_init(project_root)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
