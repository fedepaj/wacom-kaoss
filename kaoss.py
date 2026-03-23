#!/usr/bin/env python3
"""
Wacom Kaoss Pad — Turn a Wacom CTH-460 into a Kaoss Pad for Ableton Live.

2 fingers, independent XY CC pairs. ExpressKeys switch layers.
Uses hidapi (no sudo needed).

Usage: python kaoss.py
"""

import math
import signal
import struct
import sys
import time

import hid
import rtmidi

from config import (
    WACOM_VID, WACOM_PID,
    TOUCH_X_MAX, TOUCH_Y_MAX,
    MIDI_CHANNEL, TOUCH_GATE_CC,
    LAYERS, BUTTON_MASK, CURVES, EXP_CURVE_POWER,
)

running = True


def signal_handler(sig, frame):
    global running
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ─── USB via hidapi ──────────────────────────────────

def open_wacom():
    """Find CTH-460, open iface=0 for init, iface=1 for touch read."""
    devices = hid.enumerate(WACOM_VID, 0)
    if not devices:
        devices = [d for d in hid.enumerate() if d["vendor_id"] == WACOM_VID]
    if not devices:
        print("  Wacom non trovato! Collegalo via USB.")
        sys.exit(1)

    iface0_path = None
    iface1_path = None
    for d in devices:
        if d["interface_number"] == 0 and iface0_path is None:
            iface0_path = d["path"]
        elif d["interface_number"] == 1 and iface1_path is None:
            iface1_path = d["path"]

    if not iface0_path or not iface1_path:
        print("  Errore: non trovo entrambe le interfacce USB.")
        sys.exit(1)

    # Init touch via iface=0
    dev_init = hid.device()
    dev_init.open_path(iface0_path)
    try:
        dev_init.send_feature_report(bytes([0x02, 0x02]))
        print("  Touch initialized (mode 2)")
    except IOError:
        try:
            dev_init.send_feature_report(bytes([0x02, 0x03]))
            print("  Touch initialized (mode 3)")
        except IOError as e:
            print(f"  WARNING: touch init failed: {e}")
    dev_init.close()

    # Open iface=1 for reading
    dev = hid.device()
    dev.open_path(iface1_path)
    dev.set_nonblocking(True)
    print("  Touch interface open")
    return dev


def parse_touch(data):
    """Parse 20-byte Bamboo touch report."""
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

    buttons = status & 0x0F
    return fingers[0], fingers[1], buttons


# ─── MIDI ─────────────────────────────────────────────

def open_midi():
    midi = rtmidi.MidiOut()
    ports = midi.get_ports()
    print(f"  MIDI ports: {ports}")

    target_idx = None
    for i, name in enumerate(ports):
        if "IAC" in name:
            target_idx = i
            break

    if target_idx is None:
        print("\n  IAC Driver non trovato!")
        print("  Apri 'Audio MIDI Setup' > 'MIDI Studio' > abilita 'IAC Driver'")
        sys.exit(1)

    midi.open_port(target_idx)
    print(f"  MIDI output: {ports[target_idx]}")
    return midi


def send_cc(midi, cc, value):
    midi.send_message([0xB0 | MIDI_CHANNEL, cc, max(0, min(127, value))])


# ─── MAPPING ─────────────────────────────────────────

def apply_curve(value_normalized, cc):
    curve = CURVES.get(cc, 'linear')
    if curve == 'exponential':
        mapped = math.pow(value_normalized, EXP_CURVE_POWER)
    else:
        mapped = value_normalized
    return int(mapped * 127)


def get_active_layer(buttons):
    for btn_name, mask in BUTTON_MASK.items():
        if buttons & mask:
            return btn_name
    return 'base'


# ─── MAIN ────────────────────────────────────────────

def main():
    print()
    print("  ╔═══════════════════════════════════╗")
    print("  ║       WACOM KAOSS PAD             ║")
    print("  ╚═══════════════════════════════════╝")
    print()

    dev = open_wacom()
    midi = open_midi()
    print()

    was_touching = [False, False]
    last_cc = [{'x': -1, 'y': -1}, {'x': -1, 'y': -1}]
    last_layer = 'base'

    print("  Ready! Ctrl+C per uscire.\n")
    print(f"  {'LAYER':<18} {'F0 X':>5} {'Y':>5} {'CCx=v':>7} {'CCy=v':>7}  "
          f"{'F1 X':>5} {'Y':>5} {'CCx=v':>7} {'CCy=v':>7}")
    print("  " + "-" * 80)

    no_data_count = 0

    while running:
        data = dev.read(64, timeout_ms=50)

        if not data:
            no_data_count += 1
            # After ~100ms of no data, consider fingers lifted
            if no_data_count > 2:
                for fi in range(2):
                    if was_touching[fi]:
                        send_cc(midi, TOUCH_GATE_CC[fi], 0)
                        was_touching[fi] = False
                        last_cc[fi] = {'x': -1, 'y': -1}
            continue

        no_data_count = 0

        finger0, finger1, buttons = parse_touch(list(data))
        if finger0 is None:
            continue

        layer = get_active_layer(buttons)
        layer_cfg = LAYERS[layer]
        fingers = [finger0, finger1]
        display_parts = [f"  {layer_cfg['name']:<18}"]

        for fi in range(2):
            finger = fingers[fi]
            f_cfg = layer_cfg[f'f{fi}']
            cc_x_num = f_cfg['cc_x']
            cc_y_num = f_cfg['cc_y']

            if finger[0]:  # Touch active
                x_raw, y_raw = finger[1], finger[2]
                x_norm = max(0.0, min(1.0, x_raw / TOUCH_X_MAX))
                y_norm = max(0.0, min(1.0, 1.0 - (y_raw / TOUCH_Y_MAX)))

                cc_x_val = apply_curve(x_norm, cc_x_num)
                cc_y_val = apply_curve(y_norm, cc_y_num)

                if cc_x_val != last_cc[fi]['x'] or layer != last_layer:
                    send_cc(midi, cc_x_num, cc_x_val)
                    last_cc[fi]['x'] = cc_x_val
                if cc_y_val != last_cc[fi]['y'] or layer != last_layer:
                    send_cc(midi, cc_y_num, cc_y_val)
                    last_cc[fi]['y'] = cc_y_val

                if not was_touching[fi]:
                    send_cc(midi, TOUCH_GATE_CC[fi], 127)
                    was_touching[fi] = True

                display_parts.append(
                    f"{x_raw:>5} {y_raw:>5} "
                    f"CC{cc_x_num:>2}={cc_x_val:<3} CC{cc_y_num:>2}={cc_y_val:<3} ")
            else:
                if was_touching[fi]:
                    send_cc(midi, TOUCH_GATE_CC[fi], 0)
                    was_touching[fi] = False
                    last_cc[fi] = {'x': -1, 'y': -1}
                display_parts.append(f"{'---':>5} {'---':>5} {'':>7} {'':>7} ")

        last_layer = layer
        print(f"\r{''.join(display_parts)}", end="", flush=True)

    # Cleanup
    print("\n\n  Shutting down...")
    for fi in range(2):
        if was_touching[fi]:
            send_cc(midi, TOUCH_GATE_CC[fi], 0)
    midi.close_port()
    dev.close()
    print("  Done.")


if __name__ == "__main__":
    main()
