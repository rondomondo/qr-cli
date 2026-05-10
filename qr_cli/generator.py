"""
qr_cli.generator
~~~~~~~~~~~~~~~~
High-level Python API for generating styled QR codes.

    from qr_cli import generate

    result = generate(
        data="https://example.com",
        format="png",
        width=500, height=500,
        dots_color="#028f1e",
        bg_color="#ffb7ce",
        dots_type="rounded",
        corners_type="extra-rounded",
        error_correction="H",
        image="/path/to/logo.png",
        border=10,
        save_to="/tmp/qr.png",
    )
    print(result["meta"])
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

from .backends import Backend, get_backend


# ─── Public API ───────────────────────────────────────────────────────────────

def generate(
    data: str,
    *,
    format: str = "png",
    width: int = 300,
    height: Optional[int] = None,
    dots_color: str = "#000000",
    bg_color: str = "#ffffff",
    dots_type: str = "rounded",
    corners_type: Optional[str] = None,
    corners_color: Optional[str] = None,
    corner_dot_type: Optional[str] = None,
    corner_dot_color: Optional[str] = None,
    error_correction: str = "Q",
    image: Optional[str] = None,
    image_margin: int = 10,
    border: int = 0,
    margin: int = 0,
    save_to: Optional[str] = None,
    backend: Optional[Backend] = None,
    prefer_backend: Optional[str] = None,
    docker_image: Optional[str] = None,
) -> dict:
    """
    Generate a styled QR code.

    Returns the raw result dict from the rendering backend:
        {
          "success": True,
          "meta":  { format, width, height, dotsColor, bgColor, elapsed_ms, ... },
          "image": { base64, dataUri, filename, mimeType, size_bytes },
        }

    If save_to is provided, the image is written to that path and
    result["_saved_to"] is set accordingly.
    """
    if not backend:
        backend = get_backend(prefer=prefer_backend, docker_image=docker_image)

    args = _build_args(
        data=data, format=format, width=width,
        height=height or width,
        dots_color=dots_color, bg_color=bg_color,
        dots_type=dots_type,
        corners_type=corners_type, corners_color=corners_color,
        corner_dot_type=corner_dot_type, corner_dot_color=corner_dot_color,
        error_correction=error_correction,
        image=image, image_margin=image_margin,
        border=border, margin=margin,
    )

    result = backend.run(args)

    if result.get("success") and save_to:
        _save(result, save_to, format)
        result["_saved_to"] = os.path.abspath(save_to)

    return result


# ─── Arg builder ──────────────────────────────────────────────────────────────

def _build_args(**kw) -> list[str]:
    args: list[str] = []

    def a(key, val):
        if val is not None and val != "":
            args.append(f"--{key}={val}")

    a("data",   kw["data"])
    a("format", kw["format"])
    a("width",  kw["width"])
    a("height", kw["height"])
    a("border", kw.get("border", 0))
    a("margin", kw.get("margin", 0))

    a("dotsOptions.type",  kw.get("dots_type"))
    a("dotsOptions.color", kw.get("dots_color"))
    a("backgroundOptions.color", kw.get("bg_color"))

    if kw.get("corners_type"):
        a("cornersSquareOptions.type", kw["corners_type"])
    if kw.get("corners_color"):
        a("cornersSquareOptions.color", kw["corners_color"])
    if kw.get("corner_dot_type"):
        a("cornersDotOptions.type", kw["corner_dot_type"])
    if kw.get("corner_dot_color"):
        a("cornersDotOptions.color", kw["corner_dot_color"])

    a("qrOptions.errorCorrectionLevel", kw.get("error_correction", "Q"))

    if kw.get("image"):
        a("image", kw["image"])
        a("imageOptions.margin", kw.get("image_margin", 10))
        args.append("--imageOptions.crossOrigin=anonymous")

    return args


# ─── Save helper ──────────────────────────────────────────────────────────────

def _save(result: dict, path: str, fmt: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    b64 = result.get("image", {}).get("base64", "")
    if not b64:
        raise ValueError("No base64 image data in result")
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
