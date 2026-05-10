"""
qr_cli.backends
~~~~~~~~~~~~~~~
Detects and returns the best available rendering backend.

Priority:
  1. Docker  -- rondomondo/qr-cli:latest  (identical to original skill behaviour)
  2. Node    -- local node + npm install  (this package's bundled index.js)

Each backend exposes a single call:
    result = backend.run(args: list[str]) -> dict

Where args is the same --key=value list that qr-skill.sh would pass to Docker.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Optional


# ─── Abstract base ────────────────────────────────────────────────────────────

class Backend(ABC):
    name: str = "unknown"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def run(self, args: list[str]) -> dict: ...


# ─── Docker backend ───────────────────────────────────────────────────────────

class DockerBackend(Backend):
    name = "docker"
    DEFAULT_IMAGE = "rondomondo/qr-cli:latest"

    def __init__(self, image: Optional[str] = None):
        self.image = image or self.DEFAULT_IMAGE

    def available(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def run(self, args: list[str]) -> dict:
        cmd = ["docker", "run", "--rm", self.image] + args
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or f"Docker exited {result.returncode}",
            }
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON decode failed: {e}\n{result.stdout[:300]}"}


# ─── Node backend ─────────────────────────────────────────────────────────────

class NodeBackend(Backend):
    name = "node"

    def __init__(self, node_dir: Optional[str] = None):
        """
        node_dir: path to the directory containing index.js + node_modules.
        Defaults to the node/ directory bundled with this package.
        """
        import os
        self._node_dir = node_dir or os.path.join(os.path.dirname(__file__), "node")

    def available(self) -> bool:
        return bool(shutil.which("node")) and self._modules_installed()

    def _modules_installed(self) -> bool:
        import os
        nm = os.path.join(self._node_dir, "node_modules")
        return os.path.isdir(nm)

    def ensure_installed(self) -> None:
        """Run npm install in the node dir if node_modules is missing."""
        import os
        if self._modules_installed():
            return
        if not shutil.which("npm"):
            raise RuntimeError(
                "npm is required but not found. "
                "Install Node.js from https://nodejs.org/ and re-run."
            )
        subprocess.run(
            ["npm", "install", "--omit=dev"],
            cwd=self._node_dir,
            check=True,
        )

    def run(self, args: list[str]) -> dict:
        import os
        index = os.path.join(self._node_dir, "index.js")
        cmd = ["node", index] + args
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=60,
            cwd=self._node_dir,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or f"Node exited {result.returncode}",
            }
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON decode failed: {e}\n{result.stdout[:300]}"}


# ─── Selector ─────────────────────────────────────────────────────────────────

def get_backend(
    prefer: Optional[str] = None,
    docker_image: Optional[str] = None,
    node_dir: Optional[str] = None,
) -> Backend:
    """
    Returns the best available backend.

    prefer: 'docker' | 'node' | None (auto)

    Auto priority: Docker → Node.
    If Docker is preferred but unavailable, falls back to Node (with a warning).
    If Node is preferred but not installed, calls ensure_installed() first.
    """
    docker = DockerBackend(image=docker_image)
    node   = NodeBackend(node_dir=node_dir)

    if prefer == "docker":
        if docker.available():
            return docker
        import warnings
        warnings.warn(
            "Docker backend requested but not available; falling back to Node.",
            RuntimeWarning, stacklevel=2,
        )
        node.ensure_installed()
        return node

    if prefer == "node":
        node.ensure_installed()
        return node

    # Auto: Docker first
    if docker.available():
        return docker

    node.ensure_installed()
    return node
