#!/bin/bash
# Wacom Kaoss Pad — Uninstaller

PLIST_NAME="com.wacomkaoss.bridge"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
REMOTE_SCRIPT_DST="$HOME/Music/Ableton/User Library/Remote Scripts/WacomKaoss"

echo
echo "  Wacom Kaoss Pad — Uninstall"
echo

# Stop and remove LaunchAgent
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm "$PLIST_PATH"
    echo "  LaunchAgent removed"
else
    echo "  LaunchAgent not found (already removed?)"
fi

# Remove Remote Script symlink
if [ -L "$REMOTE_SCRIPT_DST" ]; then
    rm "$REMOTE_SCRIPT_DST"
    echo "  Remote Script symlink removed"
elif [ -d "$REMOTE_SCRIPT_DST" ]; then
    rm -rf "$REMOTE_SCRIPT_DST"
    echo "  Remote Script folder removed"
else
    echo "  Remote Script not found (already removed?)"
fi

echo
echo "  Done. You can safely delete this folder now."
echo
