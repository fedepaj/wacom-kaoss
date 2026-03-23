#!/usr/bin/env python3
"""
Wacom Kaoss Pad — Turn a Wacom CTH-460 into a Kaoss Pad for Ableton Live.

2 fingers, each with independent XY CC pairs. ExpressKeys switch layers.

REQUIRES SUDO: sudo .venv/bin/python kaoss.py
"""

import math
import signal
import struct
import sys
import time

import rtmidi
import usb.core
import usb.util

from config import (
    WACOM_VID, WACOM_PID, TOUCH_EP, TOUCH_IFACE, INIT_IFACE,
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


# ─── USB ──────────────────────────────────────────────

def open_wacom():
    dev = usb.core.find(idVendor=WACOM_VID, idProduct=WACOM_PID)
    if dev is None:
        dev = usb.core.find(idVendor=WACOM_VID)
    if dev is None:
        print("Wacom non trovato! Collegalo via USB.")
        sys.exit(1)

    print(f"  Device: {dev.manufacturer} {dev.product}")

    cfg = dev.get_active_configuration()
    for intf in cfg:
        n = intf.bInterfaceNumber
        try:
            if dev.is_kernel_driver_active(n):
                dev.detach_kernel_driver(n)
        except Exception:
            pass
        try:
            usb.util.claim_interface(dev, n)
        except usb.core.USBError as e:
            print(f"  Claim iface {n} failed: {e}")
            sys.exit(1)

    # Initialize touch
    try:
        dev.ctrl_transfer(0x21, 0x09, 0x0302, INIT_IFACE, bytes([0x02, 0x02]), 1000)
        print("  Touch initialized")
    except usb.core.USBError:
        try:
            dev.ctrl_transfer(0x21, 0x09, 0x0302, INIT_IFACE, bytes([0x02, 0x03]), 1000)
            print("  Touch initialized (mode 3)")
        except usb.core.USBError:
            print("  WARNING: touch init failed")

    return dev


def close_wacom(dev):
    cfg = dev.get_active_configuration()
    for intf in cfg:
        try:
            usb.util.release_interface(dev, intf.bInterfaceNumber)
            dev.attach_kernel_driver(intf.bInterfaceNumber)
        except Exception:
            pass


def parse_touch(data):
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


# ─── MAIN LOOP ───────────────────────────────────────

def main():
    print()
    print("  ╔═══════════════════════════════════╗")
    print("  ║       WACOM KAOSS PAD             ║")
    print("  ╚═══════════════════════════════════╝")
    print()

    dev = open_wacom()
    midi = open_midi()
    print()

    # Per-finger state
    was_touching = [False, False]
    last_cc = [{'x': -1, 'y': -1}, {'x': -1, 'y': -1}]
    last_layer = 'base'

    print("  Ready! 2 dita indipendenti. Bottoni = layer switch.")
    print("  Ctrl+C per uscire.\n")
    print(f"  {'LAYER':<18} {'F0 X':>5} {'Y':>5} {'CCx=v':>7} {'CCy=v':>7}  "
          f"{'F1 X':>5} {'Y':>5} {'CCx=v':>7} {'CCy=v':>7}")
    print("  " + "─" * 80)

    while running:
        try:
            data = dev.read(TOUCH_EP, 64, timeout=50)
        except usb.core.USBTimeoutError:
            # Timeout = no touch data, send gate off for any active finger
            for fi in range(2):
                if was_touching[fi]:
                    send_cc(midi, TOUCH_GATE_CC[fi], 0)
                    was_touching[fi] = False
                    last_cc[fi] = {'x': -1, 'y': -1}
            continue
        except usb.core.USBError:
            continue

        if not data:
            continue

        finger0, finger1, buttons = parse_touch(list(data))
        if finger0 is None:
            continue

        layer = get_active_layer(buttons)
        layer_cfg = LAYERS[layer]
        fingers = [finger0, finger1]
        display_parts = [f"  {layer_cfg['name']:<18}"]

        for fi in range(2):
            finger = fingers[fi]
            fkey = f'f{fi}'
            f_cfg = layer_cfg[fkey]
            cc_x_num = f_cfg['cc_x']
            cc_y_num = f_cfg['cc_y']

            if finger[0]:  # Touch active
                x_raw, y_raw = finger[1], finger[2]

                x_norm = max(0.0, min(1.0, x_raw / TOUCH_X_MAX))
                y_norm = max(0.0, min(1.0, 1.0 - (y_raw / TOUCH_Y_MAX)))

                cc_x_val = apply_curve(x_norm, cc_x_num)
                cc_y_val = apply_curve(y_norm, cc_y_num)

                # Send CCs (only on change or layer switch)
                if cc_x_val != last_cc[fi]['x'] or layer != last_layer:
                    send_cc(midi, cc_x_num, cc_x_val)
                    last_cc[fi]['x'] = cc_x_val
                if cc_y_val != last_cc[fi]['y'] or layer != last_layer:
                    send_cc(midi, cc_y_num, cc_y_val)
                    last_cc[fi]['y'] = cc_y_val

                # Touch gate
                if not was_touching[fi]:
                    send_cc(midi, TOUCH_GATE_CC[fi], 127)
                    was_touching[fi] = True

                display_parts.append(
                    f"{x_raw:>5} {y_raw:>5} "
                    f"CC{cc_x_num:>2}={cc_x_val:<3} CC{cc_y_num:>2}={cc_y_val:<3} ")
            else:
                # Finger lifted
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
    close_wacom(dev)
    print("  Done.")


if __name__ == "__main__":
    main()
