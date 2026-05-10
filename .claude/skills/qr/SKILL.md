---
name: qr
description: >
    Generate styled QR codes via the qr-cli Docker image (or Node fallback when Docker is
    unavailable). Accepts natural-language descriptions, named colours (resolved via colourmapper),
    dot/corner style keywords, logo embedding, and raw flags or JSON. Always saves the image to
    disk and reports where it landed. Use when the user wants to create, generate, or render a QR
    code for a URL or string. Triggers on phrases like "make a QR code", "generate a QR", "create
    a QR code for", "QR code this URL", "styled QR", "QR with logo", or when the user types /qr.
argument-hint: '<url> [colour] [on <bg-colour>] [rounded|circles|classy|extra-rounded] [<size>px] [svg|png|jpg|webp] [with logo <url>] [save to <path>] [--backend=docker|node|auto]'
disable-model-invocation: false
user-invocable: true
---

# /qr — QR code generator skill

Generate styled QR codes via the `qr-cli` Docker image. Accepts natural language
descriptions, named colours (resolved via `colourmapper`), or raw flags/JSON.
Always saves the image to disk and reports where it landed.

## Skill location and dependencies

All paths below are relative to the skill root (the directory containing this SKILL.md file).
When installed, that is `~/.claude/skills/qr/`.

- Wrapper:      `./scripts/qr-skill.sh`
- Docker image: `rondomondo/qr-cli:latest` (primary backend)
- Python/Node:  `python3 -m qr_cli` (automatic fallback when Docker is unavailable)

### Backend selection

The wrapper selects a backend automatically (Docker first, Node fallback):

| Situation                        | Backend used                  |
|----------------------------------|-------------------------------|
| Docker running (default)         | `docker run rondomondo/qr-cli` |
| Docker unavailable (sandbox/CI)  | `python3 -m qr_cli --backend=node` |
| `--backend=docker` forced        | Docker (errors if not running) |
| `--backend=node` forced          | Python/Node always             |
| `QR_BACKEND=node` env var        | Python/Node always             |

The Node backend is bundled with the `qr-cli` Python package. Pre-install its
Node dependencies once with:

```bash
python3 -m qr_cli --install
```

### colourmapper (required for named colour resolution)

```bash
pip install -i https://pypi.org/simple/ colourmapper-dev
```

The wrapper calls `python3 -m colourmapper.cm <name>` and falls back gracefully
to the raw value if the package is not installed.

## How to invoke

When the user types `/qr <anything>`, parse their intent and call the wrapper.
Never ask clarifying questions for reasonable defaults -- just pick them and say so.

### Examples mode

If the user types `/qr examples`, `/qr show examples`, `/qr show me the examples`,
or any phrase asking to see skill examples, try to show the most richest formatted output
you can, and to access the rich examples run:

```bash
python3 ./scripts/extract_skill_examples.py
```

Print the output verbatim (it includes ANSI colour codes that the terminal renders).
Do not call the wrapper or generate any QR code. There are sample qr code images in the 
./assets/ sub directory 

Remember that in the ./docs directory there is an EXAMPLES.md file  `./docs/EXAMPLES.md`
and a README `./docs/README.md`


### Help mode

If the user types `/qr help`, `/qr --help`, or `/qr -h`, print this reference
directly without calling the wrapper:

```
/qr <url> [options]

QUICK EXAMPLES
  /qr https://example.com
  /qr https://example.com rounded royal blue on cream
  /qr https://example.com extra-rounded midnight blue on ivory 500px
  /qr https://example.com svg slate on white
  /qr https://example.com with logo https://example.com/logo.svg

COLOURS       Any English name: "royal blue", "burnt orange", "cream", "slate",
              "ivory", "charcoal", "goldenrod", "dusty rose" -- ~30K names work.
              Hex also accepted: "#0255c7", "fff"

DOT STYLES    rounded, circles, classy, classy-round, extra-rounded, square
CORNER STYLES round corners, dot corners, square corners
FORMATS       png (default), svg, jpg, webp
SIZE          e.g. 400px, 600x400
QUALITY       use --qrOptions.errorCorrectionLevel=H when adding a logo
SAVE PATH     save to /my/path/qr.png

FLAGS (raw passthrough also works)
  --data=        URL or string to encode (required)
  --format=      png | jpg | webp | svg
  --width=       pixels (default 300)
  --height=      pixels (default 300)
  --border=      pixel border (default 10)
  --margin=      quiet zone (default 0)
  --project=     namespaces output as assets/images/<name>/qr.<ext>
  --image=       logo URL to embed in centre
  --dotsOptions.type=
  --cornersSquareOptions.type=
  --qrOptions.errorCorrectionLevel=  L | M | Q | H
```

### Colour resolution

Pass any colour the user names using `--dots-color=`, `--bg-color=`,
`--corners-color=`, `--corner-dot-color=`. The wrapper resolves them to hex via
`colourmapper` (30K named colours -- "royal blue", "cream", "burnt orange",
"slate", etc. all work). You can also pass hex directly.

If the user says "dark" / "light" without specifying a colour, default to
`--dots-color="#000000"` / `--bg-color="#ffffff"`.

### Dot style shortcuts (map natural language to --dotsOptions.type)

| User says              | Flag value        |
|------------------------|-------------------|
| round / rounded        | `rounded`         |
| circle / circles       | `dots`            |
| classy                 | `classy`          |
| classy round / elegant | `classy-rounded`  |
| extra round / bubbly   | `extra-rounded`   |
| square (default)       | `square`          |

### Corner style shortcuts (--cornersSquareOptions.type)

| User says              | Flag value        |
|------------------------|-------------------|
| round corners          | `extra-rounded`   |
| dot corners            | `dot`             |
| square corners         | `square`          |

### Error correction shortcuts (--qrOptions.errorCorrectionLevel)

| User says                           | Level |
|-------------------------------------|-------|
| low / small / fast                  | `L`   |
| medium / normal                     | `M`   |
| standard / default (omit)           | `Q`   |
| high / logo / image / best          | `H`   |

### Format shortcuts

| User says          | --format |
|--------------------|----------|
| svg / vector       | `svg`    |
| jpg / jpeg         | `jpg`    |
| webp               | `webp`   |
| png (default)      | `png`    |

## Wrapper flags reference

```
--data=<url>                  (required) string/URL to encode
--format=<png|jpg|webp|svg>   output format (default: png)
--width=<px>                  width in pixels (default: 300)
--height=<px>                 height in pixels (default: 300)
--border=<px>                 pixel border around QR (default: 10)
--margin=<px>                 quiet zone (default: 0)
--project=<name>              namespaces output as assets/images/<name>/qr.<ext>
--dotsOptions.type=<style>    dot shape (see table above)
--dotsOptions.color=<hex>     dot colour (use --dots-color= for name resolution)
--backgroundOptions.color=<hex>  background (use --bg-color= for name resolution)
--cornersSquareOptions.type=<style>
--cornersSquareOptions.color=<hex>   (use --corners-color= for name resolution)
--cornersDotOptions.type=<style>
--cornersDotOptions.color=<hex>      (use --corner-dot-color= for name resolution)
--qrOptions.errorCorrectionLevel=<L|M|Q|H>
--image=<url>                 logo URL to embed in centre
--imageOptions.margin=<px>    logo margin (default: 10)
--imageOptions.crossOrigin=anonymous   required for external logos
--save-to=<path>              override save path
--no-save                     skip writing to disk
--image-tag=<tag>             override docker image tag
--backend=<docker|node|auto>  force backend (default: auto -- Docker if available, else Node)
```

## Execution steps

1. Parse the user's request (natural language, flags, or JSON blob).
2. Resolve colour names using the wrapper's `--dots-color=` / `--bg-color=` etc.
3. Set sensible defaults for anything not specified:
   - format: `png`, width/height: `300`, border: `10`, margin: `0`
   - dots style: `rounded` (nicer default than `square`)
   - error correction: omit (library default `Q`) unless a logo is present, then use `H`
   - project: `default` if the user does not name one
4. Build the structured save path before calling the wrapper:
   - Pattern: `assets/images/{project}/{width}x{height}_{dotscolor}_{bgcolor}_{project}.{format}`
   - Strip the leading `#` from hex colours in the filename (e.g. `0504aa` not `#0504aa`).
     Use the raw colour name if hex is not yet known (it gets resolved inside the wrapper).
   - Example: `assets/images/default/300x300_royalblue_cream_default.png`
   - Pass it via `--save-to=<path>` so the wrapper writes there.
5. Run the wrapper using its absolute path (Claude Code's working directory is the project root, not the skill root):
   ```bash
   bash ./.claude/skills/qr/scripts/qr-skill.sh \
     --save-to="assets/images/default/300x300_royalblue_cream_default.png" \
     [other args...]
   ```
   The wrapper auto-selects Docker if available, otherwise falls back to `python3 -m qr_cli`
   (Node backend). Pass `--backend=node` to force the fallback explicitly (e.g. in sandboxes
   where Docker-in-Docker is not available). The `QR_BACKEND` env var is an alternative.
6. Parse the JSON result.
7. Open the saved image with:
   ```bash
   open <save-to path>
   ```
8. Report back clearly:
   - Saved to: `<path>`
   - Format / size / dimensions
   - Colours used (with resolved names if colourmapper matched)
   - Generation time
   - Any error from `.error`

## Example invocations (what the wrapper call looks like)

```bash
SKILL=./.claude/skills/qr/scripts/qr-skill.sh

# Minimal (project defaults to "default")
bash "$SKILL" \
  --data="https://example.com" \
  --save-to="assets/images/default/300x300_000000_ffffff_default.png"

# Natural colour names, rounded style
bash "$SKILL" \
  --data="https://example.com" \
  --dotsOptions.type=rounded \
  --dots-color="royal blue" \
  --bg-color="cream" \
  --save-to="assets/images/default/300x300_royalblue_cream_default.png" \
  --border=10 --margin=10

# With a logo (bumps error correction to H automatically)
bash "$SKILL" \
  --data="https://example.com" \
  --dotsOptions.type=extra-rounded \
  --dots-color="midnight blue" \
  --bg-color="ivory" \
  --cornersSquareOptions.type=extra-rounded \
  --corners-color="midnight blue" \
  --qrOptions.errorCorrectionLevel=H \
  --image="https://example.com/logo.svg" \
  --imageOptions.crossOrigin=anonymous \
  --imageOptions.margin=10 \
  --format=png --width=500 --height=500

# SVG vector output
bash "$SKILL" \
  --data="https://example.com" \
  --format=svg \
  --dotsOptions.type=rounded \
  --dots-color="slate blue" \
  --bg-color="white"

# Custom save path
bash "$SKILL" \
  --data="https://example.com" \
  --save-to="/tmp/my-qr.png"

# Pass raw JSON blob (useful for complex gradient configs)
bash "$SKILL" \
  --json='{"data":"https://example.com","format":"png","dotsOptions":{"type":"rounded","color":"#0255c7"},"backgroundOptions":{"color":"#fdfbd4"}}'
```

## What to report after generation

Render the saved path as a clickable markdown link using a **relative path** from
the repo root (`./`). VS Code renders relative markdown links as
clickable; `file://` URIs are NOT clickable in the VS Code markdown renderer.

```
QR code generated and saved.

  Saved to:    [assets/images/default/300x300_0504aa_ffffc2_default.png](assets/images/default/300x300_0504aa_ffffc2_default.png)
  Format:      PNG  (300x300 px, 14.2 KB)
  Dots:        rounded  #0504aa  (royal blue)
  Background:  #ffffc2  (cream)
  Backend:     Docker  (or "Node (python3 -m qr_cli)" when fallback was used)
  Generated:   42 ms
```

If the Node fallback was used (Docker unavailable), say so clearly -- e.g. "Generated via Node backend (Docker not available in this environment)."

Always append a fenced code block after the summary so the user can copy the
`open` command directly from the VS Code copy button:

````
```
open assets/images/default/300x300_0504aa_ffffc2_default.png
```
````

Use the exact relative path from `_skill.saved_to` (no `cd` prefix needed --
the user can paste this straight into a terminal from the repo root).

Rules for the link:
- Use the relative path from `_skill.saved_to` as both the link text and the href.
- The path is already relative to the working directory (e.g. `assets/images/default/300x300_0504aa_ffffc2_default.png`).
- Format: `[<relative_path>](<relative_path>)`
- Never use `file://` URIs -- they are not clickable in VS Code.

The `base64` field is stripped from the JSON by the wrapper before it is returned,
so do not reference or display it. If the user explicitly asks to see the base64
data, re-run with `--no-save` and parse the raw docker output directly.

If an error occurs, show the `.error` field from the JSON and suggest a fix.

## Colour name tips

- Any English colour name works: "burnt orange", "slate", "cream", "cobalt",
  "sage green", "dusty rose", "charcoal", "goldenrod", etc.
- Crayola names work too: "Alien Armpit", "Absolute Zero"
- Hex always works: "#0255c7", "0255c7", "#fff"
- The colourmapper will find the nearest match for approximate names
- The `cm` tool can be used to look up colours
