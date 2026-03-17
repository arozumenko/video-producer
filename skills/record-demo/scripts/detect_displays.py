#!/usr/bin/env python3
"""Detect available displays and ffmpeg capture devices on macOS.

Usage:
    python scripts/detect_displays.py

Outputs JSON with display info and ffmpeg device indices for screen recording.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys


def get_displays() -> list[dict]:
    """Get display info via system_profiler."""
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType"],
        capture_output=True,
        text=True,
    )
    displays = []
    current = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if "Resolution:" in line:
            match = re.search(r"(\d+)\s*x\s*(\d+)", line)
            if match:
                current["width"] = int(match.group(1))
                current["height"] = int(match.group(2))
                current["retina"] = "Retina" in line
        if "Main Display:" in line:
            current["main"] = "Yes" in line
    if current:
        displays.append(current)
    return displays


def get_ffmpeg_screens() -> list[dict]:
    """Get ffmpeg avfoundation screen capture devices."""
    result = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
    )
    screens = []
    for line in (result.stdout + result.stderr).splitlines():
        match = re.search(r"\[(\d+)\]\s*Capture screen\s*(\d+)", line)
        if match:
            screens.append({
                "device_index": match.group(1),
                "screen_index": int(match.group(2)),
            })
    return screens


def main():
    displays = get_displays()
    screens = get_ffmpeg_screens()

    info = {
        "displays": displays,
        "ffmpeg_screens": screens,
        "recommendation": (
            f"Use device {screens[0]['device_index']} for main display"
            if screens
            else "No capture devices found — check Screen Recording permission"
        ),
    }

    json.dump(info, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
