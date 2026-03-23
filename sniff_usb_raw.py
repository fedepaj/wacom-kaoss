#!/usr/bin/env python3
"""
Wacom CTH-460 RAW USB Sniffer — tries multiple init sequences.
REQUIRES SUDO: sudo .venv/bin/python sniff_usb_raw.py
"""

import signal
import struct
import sys
import time

import usb.core
import usb.util

WACOM_VID = 0x056A
WACOM_PID = 0x00D1

running = True


def signal_handler(sig, frame):
    global running
    print("\n--- Interrupted ---")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_report(dev, iface, report_id, length):
    try:
        ret = dev.ctrl_transfer(0xA1, 0x01, (0x03 << 8) | report_id, iface, length, 1000)
        return list(ret)
    except usb.core.USBError:
        return None


def set_report(dev, iface, report_id, data):
    try:
        ret = dev.ctrl_transfer(0x21, 0x09, (0x03 << 8) | report_id, iface, bytes(data), 1000)
        return ret
    except usb.core.USBError as e:
        return str(e)


def try_read(dev, ep, duration=2):
    """Try reading from an endpoint for a few seconds."""
    reports = []
    start = time.time()
    while running and (time.time() - start) < duration:
        try:
            data = dev.read(ep, 64, timeout=30)
            if data and len(data) > 0:
                reports.append(list(data))
        except (usb.core.USBTimeoutError, usb.core.USBError):
            pass
    return reports


def main():
    print("=" * 60)
    print("  Wacom CTH-460 — Init Probe")
    print("=" * 60)
    print()

    dev = usb.core.find(idVendor=WACOM_VID, idProduct=WACOM_PID)
    if dev is None:
        dev = usb.core.find(idVendor=WACOM_VID)
    if dev is None:
        print("Nessun device Wacom trovato!")
        sys.exit(1)

    print(f"  {dev.manufacturer} {dev.product}")
    print(f"  VID=0x{dev.idVendor:04X} PID=0x{dev.idProduct:04X}\n")

    cfg = dev.get_active_configuration()
    log = []

    # Detach and claim ALL interfaces
    for intf in cfg:
        n = intf.bInterfaceNumber
        try:
            if dev.is_kernel_driver_active(n):
                dev.detach_kernel_driver(n)
                print(f"  Detached kernel driver: iface {n}")
        except Exception:
            pass
        try:
            usb.util.claim_interface(dev, n)
            print(f"  Claimed: iface {n}")
        except usb.core.USBError as e:
            print(f"  Claim iface {n} failed: {e}")

    # ─── Phase 1: Probe feature reports ───
    print(f"\n{'='*60}")
    print("  PHASE 1: Probing feature reports")
    print(f"{'='*60}\n")

    for iface in range(2):
        print(f"  Interface {iface}:")
        for rid in range(256):
            for length in [2, 4, 8, 16, 32, 64]:
                data = get_report(dev, iface, rid, length)
                if data is not None:
                    hex_s = " ".join(f"{b:02X}" for b in data)
                    print(f"    GET report_id={rid:3d} (0x{rid:02X}) len={length:2d} -> [{hex_s}]")
                    log.append(f"GET iface={iface} rid={rid} -> [{hex_s}]")
                    break  # Got data for this report_id, skip longer lengths
        print()

    # ─── Phase 2: Try SET_REPORT init sequences ───
    print(f"{'='*60}")
    print("  PHASE 2: Trying init sequences")
    print(f"{'='*60}\n")

    init_attempts = []

    # All reasonable combinations
    for iface in [1, 0]:
        for rid in [2, 3, 4, 5, 0]:
            for mode_data in [
                [rid, 2],
                [rid, 0],
                [rid, 3],
                [rid, 4],
                [rid, 1],
            ]:
                init_attempts.append((iface, rid, mode_data))

    # Also try some known Wacom sequences with longer data
    for iface in [1, 0]:
        init_attempts.append((iface, 2, [0x02, 0x02, 0x00]))
        init_attempts.append((iface, 3, [0x03, 0x00, 0x00]))
        init_attempts.append((iface, 2, [0x02, 0x02, 0x00, 0x00]))

    success_count = 0
    for iface, rid, data in init_attempts:
        result = set_report(dev, iface, rid, data)
        hex_s = " ".join(f"{b:02X}" for b in data)
        if isinstance(result, int):
            print(f"  OK   iface={iface} rid={rid:3d} data=[{hex_s}] -> wrote {result}")
            log.append(f"SET OK iface={iface} rid={rid} data=[{hex_s}]")
            success_count += 1

            # After each successful SET, quick read from EP 0x82
            print(f"        Quick read EP 0x82 (1s)... tocca!", end="", flush=True)
            reports = try_read(dev, 0x82, 1)
            if reports:
                print(f" GOT {len(reports)} reports!")
                for r in reports[:5]:
                    hex_r = " ".join(f"{b:02X}" for b in r)
                    print(f"        -> len={len(r):2d} | {hex_r}")
                    log.append(f"  READ after SET: [{hex_r}]")
                if len(reports) > 5:
                    print(f"        ... and {len(reports)-5} more")
            else:
                print(" (nessun dato)")
        # Don't print failures to reduce noise

    print(f"\n  {success_count} SET_REPORT riusciti su {len(init_attempts)} tentativi")

    # ─── Phase 3: Try EP 0x82 with sustained read ───
    print(f"\n{'='*60}")
    print("  PHASE 3: Lettura prolungata da EP 0x82")
    print(f"{'='*60}")
    print("\n  Tocca la superficie per 5 secondi...")

    reports = try_read(dev, 0x82, 5)
    if reports:
        print(f"\n  DATI! {len(reports)} reports da EP 0x82:")
        unique = set()
        for r in reports:
            hex_r = " ".join(f"{b:02X}" for b in r)
            if hex_r not in unique:
                print(f"    len={len(r):2d} | {hex_r}")
                unique.add(hex_r)
                log.append(f"EP0x82: [{hex_r}]")
    else:
        print("\n  Nessun dato da EP 0x82.")

    # ─── Phase 4: Also try EP 0x81 (iface 0) ───
    print(f"\n  Prova anche EP 0x81 (iface 0, 3s)... tocca!")
    reports81 = try_read(dev, 0x81, 3)
    if reports81:
        print(f"  EP 0x81: {len(reports81)} reports")
        unique = set()
        for r in reports81[:10]:
            hex_r = " ".join(f"{b:02X}" for b in r)
            if hex_r not in unique:
                print(f"    len={len(r):2d} | {hex_r}")
                unique.add(hex_r)
        log.append(f"EP0x81: {len(reports81)} reports")

    # Cleanup
    for intf in cfg:
        try:
            usb.util.release_interface(dev, intf.bInterfaceNumber)
            dev.attach_kernel_driver(intf.bInterfaceNumber)
        except Exception:
            pass

    dump_path = "/Users/federicopaglioni/Documents/wacom-kaoss/hid_dump_raw.txt"
    with open(dump_path, "w") as f:
        f.write("\n".join(log))

    print(f"\n{'='*60}")
    print(f"  Dump salvato: hid_dump_raw.txt")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
