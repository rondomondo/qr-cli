#!/usr/bin/env python3
"""Extract bash code blocks from EXAMPLES.md and write a runnable shell script."""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent
SRC = HERE / "EXAMPLES.md"
DST = HERE / "scripts" / "run_examples.sh"

parser = argparse.ArgumentParser()
parser.add_argument("--project", default="daveco", help="project name substituted into examples")
parser.add_argument("--image", default="qr-cli:latest", help="docker image:tag to use")
args = parser.parse_args()

text = SRC.read_text()

# Anchoring headings to character positions lets nearest_heading() avoid a
# full re-scan per block - order is guaranteed by finditer left-to-right.
HEADING_RE = re.compile(r"^(&nbsp;(?:&nbsp;)*)\s*(.+)$", re.MULTILINE)

headings = [(m.start(), m.group(2).strip()) for m in HEADING_RE.finditer(text)]

# DOTALL needed so (.*?) matches newlines inside a fence; rstrip drops the
# trailing blank line that the closing ``` leaves in group(1).
FENCE_RE = re.compile(r"^```bash\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)
blocks_raw = [(m.start(), m.group(1).rstrip()) for m in FENCE_RE.finditer(text)]

if not blocks_raw:
    print("No bash blocks found in EXAMPLES.md", file=sys.stderr)
    sys.exit(1)

# Substitute the hard-coded project name and image reference with shell variable
# references so the generated script honours the PROJECT/IMAGE vars at runtime.
HARDCODED_PROJECT = "daveco"
HARDCODED_IMAGE = "qr-cli:latest"

blocks = []
for pos, code in blocks_raw:
    code = code.replace(f"assets/images/{HARDCODED_PROJECT}/", "assets/images/${PROJECT}/")
    code = code.replace(f"mkdir -p assets/images/{HARDCODED_PROJECT}", "mkdir -p assets/images/${PROJECT}")
    code = code.replace(f'"project":"{HARDCODED_PROJECT}"', '"project":"${PROJECT}"')
    code = code.replace(f'"project": "{HARDCODED_PROJECT}"', '"project": "${PROJECT}"')
    code = code.replace(f"--project={HARDCODED_PROJECT}", "--project=${PROJECT}")
    code = code.replace(f"docker run --rm {HARDCODED_IMAGE}", "docker run --rm ${IMAGE}")
    blocks.append((pos, code))


def nearest_heading(pos: int) -> str:
    """Return the last heading text that appears before pos."""
    label = "example"
    for hpos, htext in headings:
        if hpos < pos:
            label = htext
        else:
            break
    return label


total = len(blocks)

# Raw strings so the escapes survive write_text() into the shell script verbatim.
CYAN  = r"\033[0;36m"
GREEN = r"\033[0;32m"
BOLD  = r"\033[1m"
RESET = r"\033[0m"

lines = [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    "",
    f'PROJECT="${{PROJECT:-{args.project}}}"',
    f'IMAGE="${{IMAGE:-{args.image}}}"',
    f"TOTAL={total}",
    "",
]

for i, (pos, code) in enumerate(blocks, 1):
    heading = nearest_heading(pos)
    lines.append(
        f'printf "\\n{BOLD}[{i}/{total}]{RESET} {CYAN}{heading}{RESET}\\n"'
    )
    lines.append(code)
    lines.append("")

lines.append(
    f'printf "\\n{GREEN}Done -- all {total} example blocks ran successfully.{RESET}\\n"'
)
lines.append("")

DST.write_text("\n".join(lines) + "\n")
DST.chmod(0o755)
print(f"Wrote {total} blocks to {DST.relative_to(HERE)} (PROJECT={args.project}, IMAGE={args.image})")
