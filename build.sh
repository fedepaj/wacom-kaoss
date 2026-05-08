#!/bin/bash
# Build WacomKaoss.app
set -e
cd "$(dirname "$0")"

# Ensure venv
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet -r requirements.txt pyinstaller

echo
echo "  Building WacomKaoss.app..."
echo

pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name WacomKaoss \
    --icon assets/wacom-kaoss.icns \
    --paths . \
    --add-data "assets:assets" \
    --hidden-import hid \
    --hidden-import rtmidi \
    --hidden-import rtmidi._rtmidi \
    --hidden-import kaoss \
    --hidden-import AppKit \
    --hidden-import Foundation \
    --hidden-import PyObjCTools \
    --hidden-import objc \
    --osx-entitlements-file entitlements.plist \
    --osx-bundle-identifier com.wacomkaoss.app \
    app.py

# Add Input Monitoring description to Info.plist
PLIST="dist/WacomKaoss.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c \
    "Add :NSInputMonitoringUsageDescription string 'WacomKaoss needs Input Monitoring to read touch data from the Wacom tablet.'" \
    "$PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c \
    "Set :NSInputMonitoringUsageDescription 'WacomKaoss needs Input Monitoring to read touch data from the Wacom tablet.'" \
    "$PLIST"

echo
echo "  Done! App at: dist/WacomKaoss.app"
echo
echo "  Install: cp -r dist/WacomKaoss.app /Applications/"
echo
