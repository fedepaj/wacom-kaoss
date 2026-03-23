# Wacom Kaoss Pad — Project Brief

## Overview

Turn a Wacom CTH-460 (Bamboo Pen & Touch) into a digital Kaoss Pad for Ableton Live 12 on macOS (Apple Silicon). Capacitive touch only (no pen). Pure software solution — no external microcontroller needed.

## Hardware

- **Tablet**: Wacom CTH-460 (Bamboo Pen & Touch)
  - Capacitive multitouch surface with absolute XY coordinates
  - 4 physical ExpressKeys
  - USB HID device
- **Host**: Mac with Apple Silicon (M1 Pro), macOS, Ableton Live 12

## Architecture

```
Wacom CTH-460 (USB HID) → Python script → IAC Driver (virtual MIDI) → Ableton Live 12
```

Single Python script that:
1. Reads raw HID reports from the CTH-460
2. Parses touch XY coordinates + 4 ExpressKey states
3. Maps to MIDI CC messages
4. Sends via macOS IAC Driver (built-in virtual MIDI bus, zero setup)

### Dependencies
- `hidapi` — raw USB HID communication
- `python-rtmidi` — MIDI output via IAC Driver

## MIDI Mapping Scheme

The 4 ExpressKeys act as momentary modifier buttons. Holding a button switches which pair of MIDI CCs the XY touch controls. Releasing returns to the base layer.

| Layer          | Trigger         | CC X | CC Y | Ableton Effect           | X Parameter         | Y Parameter        |
|----------------|-----------------|------|------|--------------------------|----------------------|--------------------|
| Base (default) | No button held  | 20   | 21   | Auto Filter              | Cutoff frequency     | Resonance          |
| Layer 1        | Button 1 held   | 22   | 23   | Beat Repeat              | Grid size            | Pitch decay        |
| Layer 2        | Button 2 held   | 24   | 25   | Ping Pong Delay          | Delay time (sync)    | Feedback           |
| Layer 3        | Button 3 held   | 26   | 27   | Reverb                   | Decay time           | Dry/Wet            |
| Layer 4        | Button 4 held   | 28   | 29   | Redux + Erosion          | Bit reduction        | Erosion frequency  |

### Touch Gate

- Touch-on → send CC 30 value 127 (effect active)
- Touch-off (finger lifted) → send CC 30 value 0 (effect bypass)

This mimics the Kaoss Pad behavior: touching the surface activates the effect, lifting the finger bypasses it.

All CCs are sent on MIDI Channel 1.

## Development Plan

### Step 1 — HID Sniffing
- Enumerate USB HID devices, find CTH-460 by VID/PID
  - Wacom VID: `0x056A`, PID for CTH-460: look up or enumerate
- Dump raw HID report descriptors
- Log raw packets while touching the surface and pressing buttons
- Document the packet format: byte positions for X, Y, touch state, button bitmask

### Step 2 — Python Script (core)
- Open HID device
- Parse touch reports: extract X, Y (normalize to 0-127), touch-on/off
- Parse ExpressKey reports: detect which button(s) are held
- Determine active layer from button state
- Send appropriate MIDI CCs via `python-rtmidi` on IAC Driver
- Handle touch gate (CC 30)

#### Robustness
- Graceful handling of device disconnect/reconnect
- Clean shutdown on Ctrl+C
- Print active layer + XY values to terminal for debugging

### Step 3 — Response Curves
- Cutoff frequency: **exponential** curve (low end needs more resolution)
- All others: **linear** mapping
- Make curves configurable (config dict at top of script)

### Step 4 — Ableton Template
- Create an Audio Effect Rack with instructions for manual setup:
  - 5 chains, each containing the corresponding effect
  - MIDI map each parameter to the correct CC pair
  - CC 30 mapped to the rack's overall Dry/Wet or device on/off
- Provide a `.als` template file OR detailed setup instructions

### Step 5 (optional) — Visual Feedback
- Simple terminal UI (or optional small PyGame/tkinter window) showing:
  - Current active layer name
  - XY position as a dot on a grid
  - Touch state (active/inactive)

## File Structure

```
wacom-kaoss-pad/
├── README.md
├── requirements.txt          # hidapi, python-rtmidi
├── sniff_hid.py              # Step 1: HID report dumper
├── kaoss.py                  # Step 2-3: main script
├── config.py                 # Effect mappings, CC numbers, curves
└── ableton/
    └── SETUP.md              # Ableton Effect Rack setup guide
```

## Notes

- The CTH-460 may expose multiple HID interfaces (pen, touch, buttons). The script needs to open the correct one(s) — possibly multiple.
- ExpressKeys might be on a separate HID interface from touch.
- IAC Driver must be enabled in Audio MIDI Setup (macOS) — add a note in README.
- The script should work as a standalone CLI tool: `python kaoss.py` and go.
