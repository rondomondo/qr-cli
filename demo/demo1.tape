# qr-cli demo
Output demo/demo.gif
Output demo/demo.mp4

# ── All Set directives MUST come before any actions ───────────
Set Width       1200
Set Height      600
Set FontSize    14
Set FontFamily  "JetBrains Mono"
Set Theme       "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Padding     20
Set Shell       "bash"

Require make
Require jq
Require python3

# ── Suppress venv prompt prefix before recording starts ───────
Hide
Type "export VIRTUAL_ENV_DISABLE_PROMPT=1 && export PS1='$ ' && clear"
Enter
Sleep 1s
Show

# ── Section 1: show available targets ─────────────────────────
Type "make help"
Enter
Sleep 3s

# ── Section 2: run the examples target ────────────────────────
Sleep 1s
Type "make examples"
Enter
Sleep 90s

# ── Section 3: run the examples target ────────────────────────
Sleep 1s
Type "make skill-examples"
Enter
Sleep 90s

# ── End ───────────────────────────────────────────────────────
Sleep 1s
