#!/usr/bin/env python3
"""
Wacom CTH-460 HID Sniffer — Scansione automatica di tutte le interfacce.
Apre una interfaccia alla volta, fa 3 test rapidi, salva tutto in hid_dump.txt.
"""

import signal
import sys
import time

import hid

WACOM_VID = 0x056A
running = True


def signal_handler(sig, frame):
    global running
    print("\n--- Interrupted ---")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


LABELS = {
    (0xFF00, 0x0001): "VENDOR",
    (0x000D, 0x0022): "FINGER",
    (0x000D, 0x0001): "PEN",
    (0x0001, 0x0002): "MOUSE",
    (0x0001, 0x0001): "POINTER",
}


def label_for(d):
    return LABELS.get((d["usage_page"], d["usage"]),
                      f"0x{d['usage_page']:04X}/0x{d['usage']:04X}")


def read_reports(dev, duration):
    """Read all reports for `duration` seconds. Returns list of (time, bytes)."""
    reports = []
    start = time.time()
    while running and (time.time() - start) < duration:
        data = dev.read(64, 10)
        if data:
            reports.append((time.time() - start, list(data)))
    return reports


def hex_str(data):
    return " ".join(f"{b:02X}" for b in data)


def main():
    print("=" * 60)
    print("  Wacom CTH-460 — Full HID Scan")
    print("=" * 60)
    print()

    devices = hid.enumerate(WACOM_VID, 0)
    if not devices:
        devices = [d for d in hid.enumerate() if d["vendor_id"] == WACOM_VID]
    if not devices:
        print("Nessun device Wacom trovato!")
        sys.exit(1)

    print(f"Trovate {len(devices)} interfacce:\n")
    for i, d in enumerate(devices):
        print(f"  [{i}] {label_for(d):10s}  usage_page=0x{d['usage_page']:04X} "
              f"usage=0x{d['usage']:04X}  iface={d['interface_number']}")
    print()

    log = []
    log.append("WACOM CTH-460 HID DUMP")
    log.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log.append("")

    tests = [
        ("IDLE",    "NON toccare niente. Mani lontane.",                   3),
        ("TOUCH",   "Trascina il dito LENTAMENTE da alto-sx a basso-dx.", 5),
        ("TAP",     "Tocca e solleva il dito 5 volte (tap tap tap).",     5),
        ("BTN1",    "Premi e TIENI solo BOTTONE 1. NON toccare.",         3),
        ("BTN4",    "Premi e TIENI solo BOTTONE 4. NON toccare.",         3),
        ("BTN+TOUCH", "Tieni BOTTONE 1 e trascina il dito.",             4),
    ]

    for i, d in enumerate(devices):
        if not running:
            break

        lbl = label_for(d)
        header = f"INTERFACE [{i}] {lbl} (usage_page=0x{d['usage_page']:04X} usage=0x{d['usage']:04X} iface={d['interface_number']})"

        print(f"\n{'='*60}")
        print(f"  {header}")
        print(f"{'='*60}")

        log.append("")
        log.append("=" * 60)
        log.append(header)
        log.append("=" * 60)

        dev = hid.device()
        try:
            dev.open_path(d["path"])
        except IOError as e:
            msg = f"  SKIP: non riesco ad aprire ({e})"
            print(msg)
            log.append(msg)
            continue

        dev.set_nonblocking(True)
        print("  Aperta OK\n")

        for test_name, instruction, duration in tests:
            if not running:
                break

            print(f"  --- {test_name} ---")
            print(f"  {instruction}")
            print(f"  Premi ENTER quando sei pronto...", end="", flush=True)
            try:
                input()
            except EOFError:
                break

            print(f"  Recording {duration}s...", end="", flush=True)
            reports = read_reports(dev, duration)
            print(f" {len(reports)} reports")

            log.append(f"")
            log.append(f"--- {test_name}: {instruction}")

            if not reports:
                log.append("  (nessun report)")
                print("  (nessun report)")
                continue

            # Log all unique reports with timestamps
            seen = set()
            for t, data in reports:
                h = hex_str(data)
                key = tuple(data)
                if key not in seen:
                    log.append(f"  t={t:6.3f} len={len(data):2d} | {h}")
                    seen.add(key)

            # Summary
            lengths = set(len(data) for _, data in reports)
            first_bytes = set(data[0] for _, data in reports)
            all_zero = all(all(b == 0 for b in data[1:]) for _, data in reports)

            summary = (f"  => {len(reports)} reports, {len(seen)} unique, "
                       f"lengths={lengths}, report_ids={[f'0x{b:02X}' for b in sorted(first_bytes)]}"
                       f"{', ALL ZERO (no data)' if all_zero else ''}")
            print(summary)
            log.append(summary)

        dev.close()
        print(f"\n  Chiusa [{i}].")

        if i < len(devices) - 1 and running:
            print(f"\n  Prossima interfaccia [{i+1}]. ENTER per continuare...")
            try:
                input()
            except EOFError:
                break

    # Save
    dump_path = "/Users/federicopaglioni/Documents/wacom-kaoss/hid_dump.txt"
    with open(dump_path, "w") as f:
        f.write("\n".join(log))

    print(f"\n{'='*60}")
    print(f"  FATTO! Salvato in hid_dump.txt")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
