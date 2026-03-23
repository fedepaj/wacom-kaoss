#!/bin/bash
# Wacom Kaoss Pad — Installer
# Sets up venv, installs the Remote Script for Ableton, and starts the bridge.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.wacomkaoss.bridge"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
PYTHON_PATH="${SCRIPT_DIR}/.venv/bin/python"
KAOSS_PATH="${SCRIPT_DIR}/kaoss.py"
REMOTE_SCRIPT_SRC="${SCRIPT_DIR}/remote_script"
REMOTE_SCRIPT_DST="$HOME/Music/Ableton/User Library/Remote Scripts/WacomKaoss"

echo
echo "  ╔═══════════════════════════════════╗"
echo "  ║     WACOM KAOSS PAD — Install     ║"
echo "  ╚═══════════════════════════════════╝"
echo

# ─── 1. Python venv ─────────────────────────────────
if [ ! -f "$PYTHON_PATH" ]; then
    echo "  [1/3] Creating virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
    "${SCRIPT_DIR}/.venv/bin/pip" install --quiet -r "${SCRIPT_DIR}/requirements.txt"
else
    echo "  [1/3] Virtual environment OK"
fi

# ─── 2. Ableton Remote Script (symlink) ─────────────
echo "  [2/3] Installing Ableton Remote Script..."
if [ -L "$REMOTE_SCRIPT_DST" ]; then
    rm "$REMOTE_SCRIPT_DST"
elif [ -d "$REMOTE_SCRIPT_DST" ]; then
    echo "        Removing old copy at $REMOTE_SCRIPT_DST"
    rm -rf "$REMOTE_SCRIPT_DST"
fi
mkdir -p "$(dirname "$REMOTE_SCRIPT_DST")"
ln -s "$REMOTE_SCRIPT_SRC" "$REMOTE_SCRIPT_DST"
echo "        Symlinked → $REMOTE_SCRIPT_DST"

# ─── 3. LaunchAgent (auto-start at login) ───────────
echo "  [3/3] Installing LaunchAgent..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${KAOSS_PATH}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/kaoss.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/kaoss.log</string>
    <key>ThrottleInterval</key>
    <integer>5</integer>
</dict>
</plist>
EOF
launchctl load "$PLIST_PATH"
echo "        Bridge started (runs at login)"

echo
echo "  Done! Next steps:"
echo
echo "  1. Open 'Audio MIDI Setup' → enable 'IAC Driver' (if not already)"
echo "  2. Open Ableton Live → Preferences → Link/MIDI"
echo "     Control Surface = WacomKaoss"
echo "     Input = IAC Driver"
echo
echo "  Useful commands:"
echo "    Start:  launchctl load $PLIST_PATH"
echo "    Stop:   launchctl unload $PLIST_PATH"
echo "    Logs:   tail -f ${SCRIPT_DIR}/kaoss.log"
echo
