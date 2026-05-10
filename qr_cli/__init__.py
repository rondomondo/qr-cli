"""
qr-cli
~~~~~~~~~
Python wrapper for styled QR code generation.

Renders via rondomondo/qr-cli Docker image when Docker is available,
falls back to a local Node.js runtime (auto-installed on first use).

Quick start::

    from qr_cli import generate

    result = generate(
        data="https://example.com",
        width=500, height=500,
        dots_color="#028f1e",   # emerald green
        bg_color="#ffb7ce",     # baby pink
        dots_type="rounded",
        save_to="/tmp/qr.png",
    )
    print(result["meta"])

CLI usage (drop-in for qr-skill.sh)::

    python3 -m qr_cli --data="https://example.com" --width=500 ...
"""

from .generator import generate
from .backends  import get_backend, DockerBackend, NodeBackend

__all__ = ["generate", "get_backend", "DockerBackend", "NodeBackend"]
__version__ = "0.1.0"
