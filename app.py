#!/usr/bin/env python3
"""
WacomKaoss — macOS menu bar app.
Runs the Wacom-to-MIDI bridge in the background.
"""

import os
import sys
import threading

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBezierPath,
    NSColor,
    NSCompositingOperationSourceOver,
    NSImage,
    NSImageInterpolationHigh,
    NSMenu,
    NSMenuItem,
    NSMakeRect,
    NSSize,
    NSStatusBar,
    NSSquareStatusItemLength,
)
from Foundation import NSObject, NSTimer
from PyObjCTools import AppHelper

from kaoss import Bridge

# Resolve base path (PyInstaller or source)
if hasattr(sys, '_MEIPASS'):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(BASE, 'assets', 'wacom-kaoss.png')

STATUS_COLORS = {
    Bridge.CONNECTED: (0.2, 0.8, 0.2),
    Bridge.SCANNING:  (0.9, 0.7, 0.0),
    Bridge.ERROR:     (0.9, 0.2, 0.2),
}


def make_icon(status):
    """Load app icon (18x18 for menu bar) with a colored dot overlay."""
    size = 22
    dot_size = 8

    img = NSImage.alloc().initWithSize_(NSSize(size, size))
    img.lockFocus()

    # Draw the base icon
    base = NSImage.alloc().initWithContentsOfFile_(ICON_PATH)
    if base:
        base.drawInRect_fromRect_operation_fraction_(
            NSMakeRect(0, 0, size, size),
            NSMakeRect(0, 0, base.size().width, base.size().height),
            NSCompositingOperationSourceOver,
            1.0,
        )

    # Draw status dot (bottom-right)
    r, g, b = STATUS_COLORS.get(status, (0.5, 0.5, 0.5))
    NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0).setFill()
    dot_x = size - dot_size - 1
    dot_y = 1
    path = NSBezierPath.bezierPathWithOvalInRect_(
        NSMakeRect(dot_x, dot_y, dot_size, dot_size)
    )
    path.fill()

    # White border on dot
    NSColor.whiteColor().setStroke()
    path.setLineWidth_(1.0)
    path.stroke()

    img.unlockFocus()
    img.setTemplate_(False)
    return img


class AppDelegate(NSObject):

    def applicationDidFinishLaunching_(self, notification):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSSquareStatusItemLength
        )
        self._status_item.button().setImage_(make_icon(Bridge.SCANNING))

        menu = NSMenu.alloc().init()
        self._status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            'Scanning...', None, ''
        )
        self._status_menu_item.setEnabled_(False)
        menu.addItem_(self._status_menu_item)
        menu.addItem_(NSMenuItem.separatorItem())
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            'Quit', 'terminate:', 'q'
        )
        menu.addItem_(quit_item)
        self._status_item.setMenu_(menu)

        self._bridge = Bridge(on_status=lambda s: None, on_log=lambda msg: None)
        threading.Thread(target=self._bridge.run, daemon=True).start()

        self._last_status = None
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, 'updateStatus:', None, True
        )

    def updateStatus_(self, timer):
        s = self._bridge.status
        if s != self._last_status:
            self._status_item.button().setImage_(make_icon(s))
            self._last_status = s
        labels = {
            Bridge.CONNECTED: 'Connected',
            Bridge.SCANNING: 'Scanning...',
            Bridge.ERROR: 'Error: IAC Driver',
        }
        self._status_menu_item.setTitle_(labels.get(s, s))

    def applicationWillTerminate_(self, notification):
        if self._bridge:
            self._bridge.stop()


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == '__main__':
    main()
