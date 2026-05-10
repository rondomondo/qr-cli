#!/usr/bin/env python3
"""Parse EXAMPLES.md and print the equivalent /qr skill command for each docker example."""

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent

sys.path.insert(0, str(HERE))
from colourmapper.ColourMapper import ColourMapper  # noqa: E402

_cm = ColourMapper()
SRC = HERE / "EXAMPLES.md"

HEADING_RE = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)
FENCE_RE = re.compile(r"^```bash\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)

# Matches a single docker run command (possibly multi-line via backslash continuation)
# and optionally the trailing pipe to jq/base64/output redirect.
DOCKER_CMD_RE = re.compile(
    r"docker run --rm \S+\s+((?:.*\\\n)*.*?)(?:\s*\|\s*jq.*)?$",
    re.MULTILINE,
)

text = SRC.read_text()

headings = [(m.start(), m.group(2).strip()) for m in HEADING_RE.finditer(text)]
blocks_raw = [(m.start(), m.group(1).rstrip()) for m in FENCE_RE.finditer(text)]

if not blocks_raw:
    print("No bash blocks found in EXAMPLES.md", file=sys.stderr)
    sys.exit(1)


def nearest_heading(pos: int) -> str:
    label = "example"
    for hpos, htext in headings:
        if hpos < pos:
            label = htext
        else:
            break
    return label


def extract_comment(line: str) -> str:
    """Return inline # comment text, stripped, or empty string."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return stripped.lstrip("# ").strip()
    return ""


def docker_args_to_skill(raw_args: str) -> str:
    """Convert a multi-line docker arg string to a /qr skill command."""
    # Collapse backslash continuations into a single line
    single = re.sub(r"\\\n\s*", " ", raw_args).strip()

    # Tokenise: split on spaces but respect quoted strings
    tokens = re.findall(r"""(?:"[^"]*"|'[^']*'|\S)+""", single)

    skill_parts: list[str] = []
    for tok in tokens:
        if tok in ("--rm",):
            continue
        skill_parts.append(tok)

    return "/qr " + " ".join(skill_parts)


def _parse_flags(skill_cmd: str) -> dict[str, str]:
    """Extract key=value pairs from a /qr skill command string."""
    params: dict[str, str] = {}
    # Handle --json='...' blob first -- extract nested keys
    json_match = re.search(r"--json='(\{.*\})'", skill_cmd, re.DOTALL)
    if json_match:
        import json
        try:
            blob = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            blob = {}
        # Flatten nested dicts one level deep using dot notation
        for k, v in blob.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    params[f"{k}.{sk}"] = str(sv)
            else:
                params[k] = str(v)
        return params

    for tok in re.findall(r"""--[\w.\-]+=(?:"[^"]*"|'[^']*'|\S+)""", skill_cmd):
        key, _, val = tok.partition("=")
        key = key.lstrip("-")
        val = val.strip("\"'")
        params[key] = val
    return params


# Maps flag values to plain English words used in NL descriptions
_DOTS_TYPE_NL: dict[str, str] = {
    "square": "square",
    "rounded": "rounded",
    "dots": "circles",
    "classy": "classy",
    "classy-rounded": "classy rounded",
    "extra-rounded": "extra-rounded",
}
_CORNER_SQUARE_NL: dict[str, str] = {
    "square": "square corners",
    "dot": "dot corners",
    "extra-rounded": "round corners",
}
_CORNER_DOT_NL: dict[str, str] = {
    "square": "square corner dots",
    "dot": "dot corner dots",
}
_EC_NL: dict[str, str] = {
    "L": "low error correction",
    "M": "medium error correction",
    "Q": "standard error correction",
    "H": "high error correction",
}
_FORMAT_NL: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPG",
    "jpeg": "JPG",
    "webp": "WebP",
    "svg": "SVG",
}


def _colour_label(hex_val: str) -> str:
    """Return 'hex (Name)' using nearest colour name from colourmapper, or just hex if not found."""
    result = _cm.get_colour_name(hex_val)
    if result.found:
        return f"{hex_val} ({result.name})"
    return hex_val


def skill_cmd_to_nl(skill_cmd: str) -> str:
    """Produce a short natural-language /qr command equivalent."""
    p = _parse_flags(skill_cmd)

    data = p.get("data", "https://example.com")
    parts: list[str] = [data]

    # Dot style
    dots_type = p.get("dotsOptions.type", "")
    if dots_type:
        parts.append(_DOTS_TYPE_NL.get(dots_type, dots_type))

    # Colours
    dots_color = p.get("dotsOptions.color", "")
    bg_color = p.get("backgroundOptions.color", "")
    if dots_color and bg_color:
        parts.append(f"{_colour_label(dots_color)} on {_colour_label(bg_color)}")
    elif dots_color:
        parts.append(_colour_label(dots_color))

    # Corner square style
    cs_type = p.get("cornersSquareOptions.type", "")
    if cs_type:
        parts.append(_CORNER_SQUARE_NL.get(cs_type, cs_type))

    # Corner dot style
    cd_type = p.get("cornersDotOptions.type", "")
    if cd_type:
        parts.append(_CORNER_DOT_NL.get(cd_type, cd_type))

    # Error correction
    ec = p.get("qrOptions.errorCorrectionLevel", "")
    if ec:
        parts.append(_EC_NL.get(ec, ec))

    # Format (only mention when not default png)
    fmt = p.get("format", "png")
    if fmt and fmt.lower() != "png":
        parts.append(_FORMAT_NL.get(fmt.lower(), fmt.upper()))

    # Size (only mention when non-default)
    width = p.get("width", "300")
    height = p.get("height", "300")
    if width != "300" or height != "300":
        if width == height:
            parts.append(f"{width}px")
        else:
            parts.append(f"{width}x{height}")

    # Logo
    image = p.get("image", "")
    if image:
        parts.append(f"with logo {image}")

    return "/qr " + " ".join(parts)


BOLD  = "\033[1m"
CYAN  = "\033[0;36m"
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
RESET = "\033[0m"

total_commands = 0

for block_pos, code in blocks_raw:
    heading = nearest_heading(block_pos)
    lines = code.splitlines()

    # Collect comment labels and docker commands from this block
    pending_comment = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        comment = extract_comment(line)
        if comment and not comment.startswith("mkdir"):
            pending_comment = comment
            i += 1
            continue

        # Skip disabled examples (e.g. "false && docker run ...")
        if re.match(r"\s*false\s*&&", line):
            i += 1
            continue

        if "docker run --rm" not in line:
            i += 1
            continue

        # Gather continuation lines -- either backslash continuations or lines
        # inside an open single-quoted string (multi-line --json='{ ... }')
        cmd_lines = [line]
        open_squote = line.count("'") % 2 == 1
        while i + 1 < len(lines) and (cmd_lines[-1].rstrip().endswith("\\") or open_squote):
            i += 1
            next_line = lines[i]
            cmd_lines.append(next_line)
            open_squote = "".join(cmd_lines).count("'") % 2 == 1

        # Collapse backslash continuations; preserve newlines inside quoted JSON blobs
        # by joining with a space only when a line ends with backslash.
        full_cmd = ""
        for j, l in enumerate(cmd_lines):
            stripped = l.rstrip("\\").strip()
            if j == 0:
                full_cmd = stripped
            elif cmd_lines[j - 1].rstrip().endswith("\\"):
                full_cmd += " " + stripped
            else:
                full_cmd += stripped
        # Remove "docker run --rm <image>" leaving only the qr-cli args
        qr_args = re.sub(r"^docker run --rm \S+\s*", "", full_cmd).strip()
        # Strip trailing pipe section (| jq ... > file)
        qr_args = re.sub(r"\s*\|\s*jq.*$", "", qr_args, flags=re.DOTALL).strip()

        skill_cmd = "/qr " + qr_args
        nl_cmd = skill_cmd_to_nl(skill_cmd)

        label = pending_comment or heading
        print(f"{BOLD}# {label}{RESET}")
        print(f"{CYAN}{skill_cmd}{RESET}")
        print(f"{YELLOW}{nl_cmd}{RESET}")
        print()

        pending_comment = ""
        total_commands += 1
        i += 1


print(f"{GREEN}Total: {total_commands} /qr commands{RESET}")
print()
print("Tip: you can also pipe a skill command directly to claude via HEREDOC on the command line - see below")
print()
print("claude << 'EOF'")
print("  /qr https://browserleaks.com/geo extra-rounded #185FA5 on #E6F1FB as jpg")
print("EOF")
