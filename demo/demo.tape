# qr-cli demo
Output demo/demo.gif
Output demo/demo.mp4

# ── All Set directives MUST come before any actions ───────────
Set Width 1240
Set Height 920
Set FontSize 15
Set Theme "Dracula"
Set WindowBar Colorful
Set BorderRadius 10
Set TypingSpeed 150ms
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

# ─── Hidden setup ───────────────────────────────
Hide
Type "clear"
Enter
Show

# ════════════════════════════════════════════════
# README.md
# ════════════════════════════════════════════════

Type "glow --pager --style dark --width 100 README.md"
Sleep 5s
Enter
Sleep 5s

# Scroll down through the document page by page
Space
Sleep 10s
Space
Sleep 10s
Space
Sleep 10s
Space
Sleep 10s
Space
Sleep 10s

# Pause at the bottom — let it breathe
Sleep 5s

# Jump back to top
Type "g"
Sleep 5s

# Quit the pager
Type "q"
Sleep 5s

# Clear between files
Hide
Type "clear"
Enter
Show
Sleep 3s

# ════════════════════════════════════════════════
# EXAMPLE.md
# ════════════════════════════════════════════════

Type "glow --pager --style dark --width 100 EXAMPLES.md"
Sleep 5s
Enter
Sleep 5s

# Scroll down page by page
Space
Sleep 10s
Space
Sleep 10s
Space
Sleep 10s
Space
Sleep 1s

# Pause at the bottom
Sleep 5s

# Back to top
Type "g"
Sleep 5s

# Quit
Type "q"
Sleep 5s


