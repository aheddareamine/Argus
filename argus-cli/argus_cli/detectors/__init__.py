# argus-cli/argus_cli/detectors/__init__.py
from .github_actions import detect as detect_github_actions
from .docker import detect as detect_docker
from .test_runner import detect as detect_test_runner
from .kubernetes_mock import detect as detect_kubernetes
from .prometheus_mock import detect as detect_prometheus

__all__ = [
    "detect_github_actions",
    "detect_docker",
    "detect_test_runner",
    "detect_kubernetes",
    "detect_prometheus",
]
