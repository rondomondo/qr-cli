"""
qr_cli.__main__
~~~~~~~~~~~~~~~
CLI entrypoint.  Accepts the same --key=value flags as rondomondo/qr-cli
so that qr-skill.sh can swap its Docker invocation for:

    python3 -m qr_cli [args...]

Also supports a --backend=docker|node|auto flag and --install to
pre-install Node dependencies without generating a code.
"""

from __future__ import annotations

import base64
import json
import os
import sys


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # ── Special flags consumed here, not forwarded ──────────────────────────
    prefer_backend = None
    docker_image   = None
    save_to        = None
    no_save        = False
    do_install     = False
    forward        = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--backend="):
            prefer_backend = arg.split("=", 1)[1]
        elif arg.startswith("--image-tag="):
            docker_image = arg.split("=", 1)[1]
        elif arg.startswith("--save-to="):
            save_to = arg.split("=", 1)[1]
        elif arg == "--no-save":
            no_save = True
        elif arg == "--install":
            do_install = True
        else:
            forward.append(arg)
        i += 1

    # ── --install mode ───────────────────────────────────────────────────────
    if do_install:
        from .backends import NodeBackend
        nb = NodeBackend()
        print("Installing Node.js dependencies…", file=sys.stderr)
        nb.ensure_installed()
        print("Done.", file=sys.stderr)
        sys.exit(0)

    # ── Normal generation ────────────────────────────────────────────────────
    from .backends import get_backend

    backend = get_backend(prefer=prefer_backend, docker_image=docker_image)

    result = backend.run(forward)

    if result.get("success") and save_to and not no_save:
        b64 = result.get("image", {}).get("base64", "")
        if b64:
            os.makedirs(os.path.dirname(os.path.abspath(save_to)), exist_ok=True)
            with open(save_to, "wb") as f:
                f.write(base64.b64decode(b64))
            result["_skill"] = result.get("_skill", {})
            result["_skill"]["saved_to"] = save_to

    # Strip base64 from stdout (same as original Docker wrapper behaviour)
    output = {k: v for k, v in result.items() if k != "base64"}
    if "image" in output:
        output["image"] = {k: v for k, v in output["image"].items() if k != "base64"}

    sys.stdout.write(json.dumps(output) + "\n")
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
