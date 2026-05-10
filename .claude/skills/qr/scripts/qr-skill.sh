#!/usr/bin/env bash
# Wrapper invoked by the /qr skill.
# Resolves colour names to hex via colourmapper, calls qr-cli via Docker
# (or falls back to python3 -m qr_cli when Docker is unavailable),
# decodes the base64 image to disk, and prints a structured JSON result.
#
# Usage (all args are JSON key=value pairs forwarded as --json):
#   qr-skill.sh --data="https://example.com" [--format=png] [--dots-color="royal blue"] ...
#
# Special flags handled here before forwarding:
#   --dots-color=<name|hex>
#   --bg-color=<name|hex>
#   --corners-color=<name|hex>
#   --corner-dot-color=<name|hex>
#   --save-to=<path>          override output file path
#   --no-save                 skip writing to disk (stdout JSON only)
#   --image-tag=<tag>         docker image tag (default: rondomondo/qr-cli:latest)
#   --backend=docker|node|auto  force backend (default: auto)

set -euo pipefail

IMAGE_TAG="${QR_IMAGE:-rondomondo/qr-cli:latest}"
BACKEND="${QR_BACKEND:-auto}"


# Resolve a colour name or hex to a canonical hex string using colourmapper.
# Falls back to the raw value if python3 is unavailable or colourmapper is not installed.
# Install: pip install -i https://pypi.org/simple/ colourmapper-dev
resolve_colour() {
    local raw="$1"
    if [[ -z "$raw" ]]; then echo ""; return; fi
    if ! command -v python3 &>/dev/null; then echo "$raw"; return; fi

    # If input already looks like a hex code, pass it through unchanged
    if [[ "$raw" =~ ^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$ ]]; then
        # Normalise: ensure leading #
        echo "${raw/#/#}" | sed 's/^##/#/'
        return
    fi

    local hex
    hex=$(python3 -m colourmapper.cm "$raw" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hex_value']) if d.get('found') else print('')" \
        2>/dev/null) || true

    if [[ -n "$hex" ]]; then
        echo "$hex"
    else
        echo "$raw"
    fi
}

# Parse our extended flags; collect everything else for qr-cli
declare -A QR_OPTS
dots_color_raw=""
bg_color_raw=""
corners_color_raw=""
corner_dot_color_raw=""
save_to=""
no_save=false
pass_through=()

for arg in "$@"; do
    case "$arg" in
        --dots-color=*)       dots_color_raw="${arg#*=}" ;;
        --bg-color=*)         bg_color_raw="${arg#*=}" ;;
        --corners-color=*)    corners_color_raw="${arg#*=}" ;;
        --corner-dot-color=*) corner_dot_color_raw="${arg#*=}" ;;
        --save-to=*)          save_to="${arg#*=}" ;;
        --no-save)            no_save=true ;;
        --image-tag=*)        IMAGE_TAG="${arg#*=}" ;;
        --backend=*)          BACKEND="${arg#*=}" ;;
        *)                    pass_through+=("$arg") ;;
    esac
done

# Resolve all colour names
dots_color=$(resolve_colour "$dots_color_raw")
bg_color=$(resolve_colour "$bg_color_raw")
corners_color=$(resolve_colour "$corners_color_raw")
corner_dot_color=$(resolve_colour "$corner_dot_color_raw")

# Build the final arg list for qr-cli.
# qr-cli only accepts --key=value form; the value is kept in the same array element
# so the shell never sees the bare # as a comment character.
final_args=("${pass_through[@]}")
[[ -n "$dots_color" ]]        && final_args+=("--dotsOptions.color=${dots_color}")
[[ -n "$bg_color" ]]          && final_args+=("--backgroundOptions.color=${bg_color}")
[[ -n "$corners_color" ]]     && final_args+=("--cornersSquareOptions.color=${corners_color}")
[[ -n "$corner_dot_color" ]]  && final_args+=("--cornersDotOptions.color=${corner_dot_color}")

# Run qr-cli — Docker primary, Python/Node fallback when Docker is unavailable
_docker_available() { docker info >/dev/null 2>&1; }

if [[ "$BACKEND" == "node" ]] || { [[ "$BACKEND" == "auto" ]] && ! _docker_available; }; then
    raw=$(python3 -m qr_cli --backend=node "${final_args[@]}" 2>/dev/null)
elif [[ "$BACKEND" == "docker" ]] || _docker_available; then
    raw=$(docker run --rm "$IMAGE_TAG" "${final_args[@]}" 2>/dev/null)
else
    echo '{"success":false,"error":"Docker is not running and python3 -m qr_cli (Node fallback) is unavailable. Run: pip install qr-cli && python3 -m qr_cli --install"}' >&2
    exit 1
fi

success=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success','false'))" 2>/dev/null) || true

if [[ "$success" != "True" ]]; then
    echo "$raw"
    exit 1
fi

# Optionally save to disk
if [[ "$no_save" == false ]]; then
    # Use --save-to, else fall back to meta.image.filename, else qr.<ext>
    if [[ -z "$save_to" ]]; then
        save_to=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['image']['filename'])" 2>/dev/null) || save_to="qr.png"
    fi
    mkdir -p "$(dirname "$save_to")"
    echo "$raw" | python3 -c "
import sys, json, base64, pathlib
d = json.load(sys.stdin)
pathlib.Path(sys.argv[1]).write_bytes(base64.b64decode(d['image']['base64']))
" "$save_to"

    # Inject resolved colours and save path into the output for the skill to report.
    # Strip base64 payload -- it has already been written to disk and is too large to display.
    enriched=$(echo "$raw" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'image' in d and 'base64' in d['image']:
    del d['image']['base64']
d['_skill'] = {
    'saved_to': sys.argv[1],
    'dots_color_resolved':        sys.argv[2] or None,
    'bg_color_resolved':          sys.argv[3] or None,
    'corners_color_resolved':     sys.argv[4] or None,
    'corner_dot_color_resolved':  sys.argv[5] or None,
}
print(json.dumps(d))
" "$save_to" "$dots_color" "$bg_color" "$corners_color" "$corner_dot_color")
    echo "$enriched"
else
    echo "$raw"
fi
