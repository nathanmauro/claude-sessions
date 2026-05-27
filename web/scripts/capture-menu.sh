#!/usr/bin/env bash
# Capture docs/screenshots/menubar.png by booting `agentseq menu` against
# the demo SQLite index, opening the dropdown via AppleScript, and screencapturing
# the region.
#
# Requires:
#   - .venv/bin/agentseq (pip install -e '.[menu]')
#   - Accessibility permission for the terminal running this script
#     (System Settings → Privacy & Security → Accessibility)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -x .venv/bin/agentseq ]]; then
  echo "error: .venv/bin/agentseq not found." >&2
  echo "  run: uv venv && uv pip install -e '.[menu]'" >&2
  exit 1
fi

DEMO_CACHE="/tmp/demo-agentseq"
export AGENTSEQ_CACHE="$DEMO_CACHE"

# Pre-flight: verify Accessibility permission. Test against Finder which always
# has a menu bar. Error -25211 == "not allowed assistive access".
PREFLIGHT=$(osascript -e 'tell application "System Events" to tell process "Finder" to count menu bar items of menu bar 1' 2>&1 || true)
if [[ "$PREFLIGHT" == *"not allowed"* || "$PREFLIGHT" == *"25211"* ]]; then
  cat >&2 <<EOF
error: AppleScript needs Accessibility permission for this terminal.
       osascript said: $PREFLIGHT

  Grant Accessibility to your terminal app (Terminal.app, iTerm, etc.) in:
    System Settings → Privacy & Security → Accessibility
  Then re-run this script directly from that terminal:
    bash web/scripts/capture-menu.sh
EOF
  exit 2
fi

python3 web/scripts/seed-demo-db.py >&2

# rumps registers as the python interpreter — boot it and remember the PID.
.venv/bin/agentseq menu >/tmp/agentseq-menu.log 2>&1 &
MENU_PID=$!
trap 'kill "$MENU_PID" 2>/dev/null || true' EXIT

# Give the menubar a moment to register.
sleep 2

if ! kill -0 "$MENU_PID" 2>/dev/null; then
  echo "error: menu process exited early. log:" >&2
  cat /tmp/agentseq-menu.log >&2
  exit 1
fi

# Open the dropdown and screencapture in one AppleScript pass so the menu
# stays open during capture. Headless rumps apps register their status item
# on menu bar 1 (not 2). Include some pixels above for the menubar title.
OUTPUT="docs/screenshots/menubar.png"
BOUNDS=$(osascript <<APPLESCRIPT
tell application "System Events"
  tell process "python"
    set mbi to menu bar item 1 of menu bar 1
    -- Capture the menubar item bounds BEFORE opening (after click it can shift).
    set iPos to position of mbi
    set iSize to size of mbi
    set ix to item 1 of iPos
    set iw to item 1 of iSize
    click mbi
    delay 0.4
    set theMenu to menu 1 of mbi
    set thePos to position of theMenu
    set theSize to size of theMenu
    set menuX to item 1 of thePos
    set menuY to item 2 of thePos
    set menuW to item 1 of theSize
    set menuH to item 2 of theSize
    -- Union the menubar-item x-span with the menu x-span.
    set unionX to menuX
    if ix < unionX then set unionX to ix
    set unionRight to menuX + menuW
    set itemRight to ix + iw
    if itemRight > unionRight then set unionRight to itemRight
    set unionW to unionRight - unionX
    -- Start at the top of the screen so the menubar icon row is captured.
    set startY to 0
    set unionH to (menuY + menuH) - startY
    do shell script "screencapture -x -R " & unionX & "," & startY & "," & unionW & "," & unionH & " '${REPO_ROOT}/${OUTPUT}'"
    key code 53
    return "item=" & ix & "+" & iw & " menu=" & menuX & "," & menuY & " " & menuW & "x" & menuH & " union=" & unionX & "," & startY & " " & unionW & "x" & unionH
  end tell
end tell
APPLESCRIPT
)

if [[ -z "$BOUNDS" ]]; then
  echo "error: AppleScript did not return bounds (menu interaction failed)" >&2
  exit 1
fi

echo "menu bounds: $BOUNDS" >&2
file "$OUTPUT"
ls -lh "$OUTPUT"
