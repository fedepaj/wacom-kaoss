# Wacom Kaoss Pad

Turn a **Wacom CTH-460** (Bamboo Pen & Touch) into a Kaoss Pad for **Ableton Live**.

Two-finger multitouch XY control with 5 layers switchable via the tablet's ExpressKeys — no sudo required.

## How it works

```
kaoss.py (USB → MIDI bridge)          Ableton Remote Script
┌──────────────────────────┐          ┌──────────────────────┐
│ Reads Wacom touch via    │  IAC     │ Auto-maps CCs to     │
│ hidapi, sends MIDI CCs   │ ──────→  │ device parameters    │
│ through IAC Driver       │  MIDI    │ (filter, delay, etc) │
└──────────────────────────┘          └──────────────────────┘
```

- **kaoss.py** reads 2-finger touch + buttons from the Wacom via hidapi (IOKit, no root)
- Sends MIDI CCs through macOS IAC Driver
- The **Ableton Remote Script** auto-maps those CCs to effect parameters

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.9+
- Wacom CTH-460 (Bamboo Pen & Touch)
- Ableton Live 11/12
- IAC Driver enabled (Audio MIDI Setup → MIDI Studio → IAC Driver → Device is online)

## Install

```bash
git clone https://github.com/YOUR_USER/wacom-kaoss.git
cd wacom-kaoss
./install.sh
```

This will:
1. Create a Python virtual environment and install dependencies
2. Symlink the Remote Script into Ableton's User Library
3. Start the USB→MIDI bridge as a background service (auto-starts at login)

Then in Ableton:
- **Preferences → Link/MIDI → Control Surface** = `WacomKaoss`
- **Input** = `IAC Driver`

## Layers

The 4 ExpressKeys switch between effect layers. Each layer controls 2 instances (one per finger):

| Key | Effect | X axis | Y axis |
|-----|--------|--------|--------|
| — | Auto Filter | Frequency | Resonance |
| 1 | Beat Repeat | Grid | Pitch Decay |
| 2 | Ping Pong Delay | Delay Time | Feedback |
| 3 | Reverb | Decay Time | Dry/Wet |
| 4 | Redux | Bit On | Frequency |

The Remote Script scans your Live Set for matching devices and binds automatically.

## Uninstall

```bash
./uninstall.sh
```

## Project structure

```
kaoss.py            USB→MIDI bridge (runs as background service)
config.py           All configuration (layers, CCs, curves)
remote_script/      Ableton Remote Script (symlinked by install.sh)
├── __init__.py
└── WacomKaoss.py
install.sh          One-command setup
uninstall.sh        Clean removal
```

## License

MIT
