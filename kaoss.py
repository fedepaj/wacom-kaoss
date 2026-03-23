#!/usr/bin/env python3
"""
Wacom Kaoss Pad — Turn a Wacom CTH-460 into a Kaoss Pad for Ableton Live.

Reads absolute XY touch from the Wacom via raw USB, maps to MIDI CCs
through the macOS IAC Driver. ExpressKeys switch between effect layers.

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
    MIDI_PORT_NAME, MIDI_CHANNEL, TOUCH_GATE_CC,
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
    """Find, claim, and initialize the Wacom CTH-460."""
    dev = usb.core.find(idVendor=WACOM_VID, idProduct=WACOM_PID)
    if dev is None:
        dev = usb.core.find(idVendor=WACOM_VID)
    if dev is None:
        print("Wacom non trovato! Collegalo via USB.")
        sys.exit(1)

    print(f"  Device: {dev.manufacturer} {dev.product}")

    cfg = dev.get_active_configuration()

    # Detach kernel drivers and claim both interfaces
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

    # Initialize touch: SET_REPORT Feature report_id=2, mode=2 on iface 0
    try:
        dev.ctrl_transfer(0x21, 0x09, 0x0302, INIT_IFACE, bytes([0x02, 0x02]), 1000)
        print("  Touch initialized")
    except usb.core.USBError as e:
        print(f"  Touch init failed: {e}")
        # Try mode 3 as fallback
        try:
            dev.ctrl_transfer(0x21, 0x09, 0x0302, INIT_IFACE, bytes([0x02, 0x03]), 1000)
            print("  Touch initialized (mode 3)")
        except usb.core.USBError:
            print("  WARNING: touch init failed, continuing anyway...")

    return dev


def close_wacom(dev):
    """Release interfaces and reattach kernel drivers."""
    cfg = dev.get_active_configuration()
    for intf in cfg:
        try:
            usb.util.release_interface(dev, intf.bInterfaceNumber)
            dev.attach_kernel_driver(intf.bInterfaceNumber)
        except Exception:
            pass


def parse_touch(data):
    """Parse a 20-byte Bamboo touch report.
    Returns (finger0, finger1, buttons) where finger = (active, x, y) or None.
    """
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
    """Open MIDI output on IAC Driver."""
    midi = rtmidi.MidiOut()
    ports = midi.get_ports()

    print(f"  MIDI ports: {ports}")

    # Find IAC Driver
    target_idx = None
    for i, name in enumerate(ports):
        if "IAC" in name:
            target_idx = i
            break

    if target_idx is None:
        print(f"\n  IAC Driver non trovato!")
        print("  Apri 'Audio MIDI Setup' > mostra 'MIDI Studio' > abilita 'IAC Driver'")
        sys.exit(1)

    midi.open_port(target_idx)
    print(f"  MIDI output: {ports[target_idx]}")
    return midi


def send_cc(midi, cc, value):
    """Send a MIDI CC message."""
    midi.send_message([0xB0 | MIDI_CHANNEL, cc, max(0, min(127, value))])


# ─── MAPPING ─────────────────────────────────────────

def apply_curve(value_normalized, cc):
    """Apply response curve. value_normalized is 0.0-1.0, returns 0-127."""
    curve = CURVES.get(cc, 'linear')
    if curve == 'exponential':
        mapped = math.pow(value_normalized, EXP_CURVE_POWER)
    else:
        mapped = value_normalized
    return int(mapped * 127)


def get_active_layer(buttons):
    """Determine active layer from button bitmask."""
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

    was_touching = False
    last_layer = 'base'
    last_cc_x = -1
    last_cc_y = -1

    print("  Ready! Tocca la superficie per controllare gli effetti.")
    print("  Ctrl+C per uscire.\n")
    print(f"  {'LAYER':<20} {'X':>5} {'Y':>5}  {'CC_X':>4}={'val':<3} {'CC_Y':>4}={'val':<3}")
    print("  " + "─" * 55)

    while running:
        try:
            data = dev.read(TOUCH_EP, 64, timeout=50)
        except usb.core.USBTimeoutError:
            # No data = finger lifted (if we were touching)
            if was_touching:
                send_cc(midi, TOUCH_GATE_CC, 0)
                was_touching = False
                print(f"\r  {'(touch off)':<55}", end="", flush=True)
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

        if finger0[0]:  # Touch active
            x_raw, y_raw = finger0[1], finger0[2]

            # Normalize to 0.0-1.0
            x_norm = x_raw / TOUCH_X_MAX
            y_norm = y_raw / TOUCH_Y_MAX

            # Invert Y (tablet Y=0 is bottom, we want Y=0 at top)
            y_norm = 1.0 - y_norm

            # Clamp
            x_norm = max(0.0, min(1.0, x_norm))
            y_norm = max(0.0, min(1.0, y_norm))

            # Apply curves and get MIDI values
            cc_x_num = layer_cfg['cc_x']
            cc_y_num = layer_cfg['cc_y']
            cc_x_val = apply_curve(x_norm, cc_x_num)
            cc_y_val = apply_curve(y_norm, cc_y_num)

            # Send MIDI CCs (only if changed)
            if cc_x_val != last_cc_x or layer != last_layer:
                send_cc(midi, cc_x_num, cc_x_val)
                last_cc_x = cc_x_val
            if cc_y_val != last_cc_y or layer != last_layer:
                send_cc(midi, cc_y_num, cc_y_val)
                last_cc_y = cc_y_val

            # Touch gate
            if not was_touching:
                send_cc(midi, TOUCH_GATE_CC, 127)
                was_touching = True

            last_layer = layer

            # Terminal display
            print(f"\r  {layer_cfg['name']:<20} "
                  f"{x_raw:>5} {y_raw:>5}  "
                  f"CC{cc_x_num:>2}={cc_x_val:<3} CC{cc_y_num:>2}={cc_y_val:<3}",
                  end="", flush=True)

        else:
            # No touch
            if was_touching:
                send_cc(midi, TOUCH_GATE_CC, 0)
                was_touching = False
                last_cc_x = -1
                last_cc_y = -1
                print(f"\r  {'(touch off)':<55}", end="", flush=True)

    # Cleanup
    print("\n\n  Shutting down...")
    if was_touching:
        send_cc(midi, TOUCH_GATE_CC, 0)
    midi.close_port()
    close_wacom(dev)
    print("  Done.")


if __name__ == "__main__":
    main()
