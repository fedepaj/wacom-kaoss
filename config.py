# Wacom Kaoss Pad — Configuration

# ─── USB ──────────────────────────────────────────────
WACOM_VID = 0x056A
WACOM_PID = 0x00D1  # CTH-460 Bamboo Pen & Touch
TOUCH_EP = 0x82
PEN_EP = 0x81
TOUCH_IFACE = 1
INIT_IFACE = 0  # SET_REPORT goes to iface 0

# Touch resolution (from real device testing)
TOUCH_X_MAX = 480
TOUCH_Y_MAX = 320

# ─── MIDI ─────────────────────────────────────────────
MIDI_PORT_NAME = "IAC Driver Bus 1"  # macOS IAC virtual MIDI
MIDI_CHANNEL = 0  # Channel 1 (0-indexed)

# Touch gate CCs (per finger)
TOUCH_GATE_CC = [30, 31]  # finger 0, finger 1

# ─── LAYERS ───────────────────────────────────────────
# Each layer: 2 fingers, each with cc_x/cc_y
LAYERS = {
    'base': {
        'name': 'Auto Filter',
        'f0': {'cc_x': 20, 'cc_y': 21},  # Finger 0: Cutoff / Resonance
        'f1': {'cc_x': 22, 'cc_y': 23},  # Finger 1: Cutoff / Resonance (2nd filter)
    },
    'btn1': {
        'name': 'Beat Repeat',
        'f0': {'cc_x': 24, 'cc_y': 25},
        'f1': {'cc_x': 26, 'cc_y': 27},
    },
    'btn2': {
        'name': 'Ping Pong Delay',
        'f0': {'cc_x': 28, 'cc_y': 29},
        'f1': {'cc_x': 32, 'cc_y': 33},
    },
    'btn3': {
        'name': 'Reverb',
        'f0': {'cc_x': 34, 'cc_y': 35},
        'f1': {'cc_x': 36, 'cc_y': 37},
    },
    'btn4': {
        'name': 'Redux + Erosion',
        'f0': {'cc_x': 38, 'cc_y': 39},
        'f1': {'cc_x': 40, 'cc_y': 41},
    },
}

# ─── BUTTON BITMASK (from HID sniffing) ──────────────
BUTTON_MASK = {
    'btn1': 0x08,  # bit 3
    'btn2': 0x04,  # bit 2
    'btn3': 0x02,  # bit 1
    'btn4': 0x01,  # bit 0
}

# ─── RESPONSE CURVES ─────────────────────────────────
# 'linear' or 'exponential' — keyed by CC number
CURVES = {
    20: 'exponential',  # Auto Filter cutoff
    22: 'exponential',  # Auto Filter 2 cutoff
}
# All CCs not listed default to 'linear'

# Exponential curve exponent (higher = more low-end resolution)
EXP_CURVE_POWER = 2.0
