#!/usr/bin/env python3
"""
Wacom Kaoss Pad — Turn a Wacom CTH-460 into a Kaoss Pad for Ableton Live.

2 fingers, independent XY CC pairs. ExpressKeys switch 5 effect layers.
Uses hidapi (no sudo). Auto-reconnects. EMA smoothing + grace period.

Usage: python kaoss.py
"""

import math
import signal
import struct
import sys
import time

import hid
import rtmidi

# ─── Config ──────────────────────────────────────────

WACOM_VID = 0x056A
WACOM_PID = 0x00D1  # CTH-460 Bamboo Pen & Touch

TOUCH_X_MAX = 480
TOUCH_Y_MAX = 320

MIDI_CHANNEL = 0  # Channel 1

LAYERS = {
    'base': {
        'name': 'Auto Filter',
        'f0': {'cc_x': 20, 'cc_y': 21},
        'f1': {'cc_x': 22, 'cc_y': 23},
        'gate': [30, 31],
    },
    'btn1': {
        'name': 'Beat Repeat',
        'f0': {'cc_x': 24, 'cc_y': 25},
        'f1': {'cc_x': 26, 'cc_y': 27},
        'gate': [42, 43],
    },
    'btn2': {
        'name': 'Ping Pong Delay',
        'f0': {'cc_x': 28, 'cc_y': 29},
        'f1': {'cc_x': 32, 'cc_y': 33},
        'gate': [44, 45],
    },
    'btn3': {
        'name': 'Reverb',
        'f0': {'cc_x': 34, 'cc_y': 35},
        'f1': {'cc_x': 36, 'cc_y': 37},
        'gate': [46, 47],
    },
    'btn4': {
        'name': 'Redux',
        'f0': {'cc_x': 38, 'cc_y': 39},
        'f1': {'cc_x': 40, 'cc_y': 41},
        'gate': [48, 49],
    },
}

BUTTON_MASK = {
    'btn1': 0x08,
    'btn2': 0x04,
    'btn3': 0x02,
    'btn4': 0x01,
}

# Response curves: exponential for filter cutoffs, linear for the rest
EXP_CURVES = {20, 22}
EXP_POWER = 2.0

# Smoothing / error correction
EMA_ALPHA = 0.3          # 0.0 = full smoothing, 1.0 = no smoothing
CC_THRESHOLD = 2          # minimum CC change to send
GRACE_CYCLES = 8          # missed read cycles before releasing (8 * 50ms = 400ms)
READ_TIMEOUT_MS = 50


# ─── Parsing ─────────────────────────────────────────

def parse_touch(data):
    """Parse 20-byte Bamboo touch report → (finger0, finger1, buttons)."""
    if len(data) < 20 or data[0] != 0x02:
        return None, None, 0

    status = data[1]
    alt = bool(status & 0x80)

    fingers = []
    for i in range(2):
        offset = (8 * i) if alt else (9 * i)
        touch = bool(data[offset + 3] & 0x80)
        if touch:
            x = struct.unpack('>H', bytes(data[offset + 3:offset + 5]))[0] & 0x7FF
            y = struct.unpack('>H', bytes(data[offset + 5:offset + 7]))[0] & 0x7FF
            fingers.append((True, x, y))
        else:
            fingers.append((False, 0, 0))

    return fingers[0], fingers[1], status & 0x0F


def apply_curve(norm, cc):
    if cc in EXP_CURVES:
        return int(math.pow(norm, EXP_POWER) * 127)
    return int(norm * 127)


def get_layer(buttons):
    for name, mask in BUTTON_MASK.items():
        if buttons & mask:
            return name
    return 'base'


# ─── Bridge ──────────────────────────────────────────

class Bridge:
    """Wacom USB -> MIDI bridge with auto-reconnect and smoothing."""

    SCANNING = 'scanning'
    CONNECTED = 'connected'
    ERROR = 'error'

    def __init__(self, on_status=None, on_log=None):
        self.on_status = on_status
        self.on_log = on_log
        self.running = True
        self.status = self.SCANNING
        self._dev = None
        self._midi = None
        self._reset_touch_state()

    def _reset_touch_state(self):
        self._was_touching = [False, False]
        self._ema = [{'x': None, 'y': None}, {'x': None, 'y': None}]
        self._last_sent = [{'x': -1, 'y': -1}, {'x': -1, 'y': -1}]
        self._last_layer = 'base'

    def log(self, msg):
        if self.on_log:
            self.on_log(msg)
        else:
            print(f"  {msg}")

    def _set_status(self, status):
        self.status = status
        if self.on_status:
            self.on_status(status)

    # ─── Main loop ───────────────────────────────────

    def run(self):
        """Blocks until stop()."""
        while self.running:
            if self._midi is None:
                self._midi = self._open_midi()
                if self._midi is None:
                    self._set_status(self.ERROR)
                    self._sleep(5)
                    continue

            self._set_status(self.SCANNING)
            dev = self._try_connect()
            if dev is None:
                self._sleep(2)
                continue

            self._dev = dev
            self._set_status(self.CONNECTED)
            self._read_loop()
            self._close_device()

            if self.running:
                self.log("Device lost, scanning...")

        self._cleanup()

    def stop(self):
        self.running = False

    def _sleep(self, seconds):
        end = time.time() + seconds
        while self.running and time.time() < end:
            time.sleep(0.1)

    # ─── USB ─────────────────────────────────────────

    def _try_connect(self):
        try:
            devices = hid.enumerate(WACOM_VID, 0)
            if not devices:
                devices = [d for d in hid.enumerate() if d['vendor_id'] == WACOM_VID]
            if not devices:
                return None

            iface0 = [d['path'] for d in devices if d['interface_number'] == 0]
            iface1 = [d['path'] for d in devices if d['interface_number'] == 1]
            if not iface0 or not iface1:
                return None

            # Init touch on iface 0
            for path in iface0:
                try:
                    d = hid.device()
                    d.open_path(path)
                    try:
                        d.send_feature_report(bytes([0x02, 0x02]))
                        self.log("Touch init OK")
                    except IOError:
                        try:
                            d.send_feature_report(bytes([0x02, 0x03]))
                            self.log("Touch init OK (mode 3)")
                        except IOError:
                            pass
                    d.close()
                    break
                except OSError:
                    continue

            # Open iface 1 for reading
            for path in iface1:
                try:
                    d = hid.device()
                    d.open_path(path)
                    d.set_nonblocking(True)
                    self.log("Data interface open")
                    return d
                except OSError:
                    continue

            return None
        except Exception as e:
            self.log(f"Connect error: {e}")
            return None

    # ─── MIDI ────────────────────────────────────────

    def _open_midi(self):
        try:
            midi = rtmidi.MidiOut()
            for i, name in enumerate(midi.get_ports()):
                if 'IAC' in name:
                    midi.open_port(i)
                    self.log(f"MIDI: {name}")
                    return midi
            self.log("IAC Driver not found — enable in Audio MIDI Setup")
            return None
        except Exception as e:
            self.log(f"MIDI error: {e}")
            return None

    def _send_cc(self, cc, value):
        if self._midi:
            try:
                self._midi.send_message([0xB0 | MIDI_CHANNEL, cc, max(0, min(127, value))])
            except Exception:
                pass

    # ─── Read loop ───────────────────────────────────

    def _read_loop(self):
        no_data = [0, 0]  # per-finger grace counters

        while self.running:
            try:
                data = self._dev.read(64, timeout_ms=READ_TIMEOUT_MS)
            except OSError:
                self.log("Read error — device lost")
                return

            if not data:
                # Grace period: increment per-finger counters
                for fi in range(2):
                    if self._was_touching[fi]:
                        no_data[fi] += 1
                        if no_data[fi] >= GRACE_CYCLES:
                            self._release_finger(fi)
                continue

            f0, f1, buttons = parse_touch(list(data))
            if f0 is None:
                continue

            layer = get_layer(buttons)
            cfg = LAYERS[layer]
            prev_layer = self._last_layer

            # Layer changed while touching: release on old layer, re-gate on new
            if layer != prev_layer:
                prev_cfg = LAYERS[prev_layer]
                for fi in range(2):
                    if self._was_touching[fi]:
                        self._send_cc(prev_cfg['gate'][fi], 0)
                        self._send_cc(cfg['gate'][fi], 127)

            for fi, finger in enumerate((f0, f1)):
                fc = cfg[f'f{fi}']

                if finger[0]:  # touching
                    no_data[fi] = 0
                    x_norm = max(0.0, min(1.0, finger[1] / TOUCH_X_MAX))
                    y_norm = max(0.0, min(1.0, 1.0 - finger[2] / TOUCH_Y_MAX))

                    # EMA smoothing
                    if self._ema[fi]['x'] is None:
                        self._ema[fi]['x'] = x_norm
                        self._ema[fi]['y'] = y_norm
                    else:
                        self._ema[fi]['x'] += EMA_ALPHA * (x_norm - self._ema[fi]['x'])
                        self._ema[fi]['y'] += EMA_ALPHA * (y_norm - self._ema[fi]['y'])

                    cc_x = apply_curve(self._ema[fi]['x'], fc['cc_x'])
                    cc_y = apply_curve(self._ema[fi]['y'], fc['cc_y'])

                    # Send only if changed enough (or layer switch)
                    if abs(cc_x - self._last_sent[fi]['x']) >= CC_THRESHOLD or layer != prev_layer:
                        self._send_cc(fc['cc_x'], cc_x)
                        self._last_sent[fi]['x'] = cc_x
                    if abs(cc_y - self._last_sent[fi]['y']) >= CC_THRESHOLD or layer != prev_layer:
                        self._send_cc(fc['cc_y'], cc_y)
                        self._last_sent[fi]['y'] = cc_y

                    if not self._was_touching[fi]:
                        self._send_cc(cfg['gate'][fi], 127)
                        self._was_touching[fi] = True

                else:  # not touching in this report
                    if self._was_touching[fi]:
                        no_data[fi] += 1
                        if no_data[fi] >= GRACE_CYCLES:
                            self._release_finger(fi)

            self._last_layer = layer

    def _release_finger(self, fi):
        cfg = LAYERS[self._last_layer]
        self._send_cc(cfg['gate'][fi], 0)
        self._was_touching[fi] = False
        self._ema[fi] = {'x': None, 'y': None}
        self._last_sent[fi] = {'x': -1, 'y': -1}

    # ─── Cleanup ─────────────────────────────────────

    def _close_device(self):
        if self._dev:
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None
        self._reset_touch_state()

    def _cleanup(self):
        for fi in range(2):
            if self._was_touching[fi]:
                cfg = LAYERS[self._last_layer]
                self._send_cc(cfg['gate'][fi], 0)
        self._close_device()
        if self._midi:
            try:
                self._midi.close_port()
            except Exception:
                pass
            self._midi = None


# ─── CLI ─────────────────────────────────────────────

def main():
    print()
    print("  WACOM KAOSS PAD")
    print("  ───────────────")
    print()

    bridge = Bridge(
        on_status=lambda s: print(f"  [{s}]"),
    )

    def on_signal(sig, frame):
        bridge.stop()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    bridge.run()
    print("\n  Done.")


if __name__ == '__main__':
    main()
