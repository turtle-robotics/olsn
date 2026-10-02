# -*- coding: utf-8 -*-
"""
Probe COM13–COM16 for a BITalino reachable over Bluetooth SPP (serial).

Run from this folder:
  python try_bluetooth_com_ports.py

Adjust PORTS, SamplingRate, or channels below if needed.
"""

from __future__ import print_function

import os
import sys
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from bitalino import BITalino


def windows_serial_device(port_name):
    """
    COM10 and above on Windows should use the \\\\.\\COMxx form for CreateFile.
    """
    name = port_name.strip().upper()
    if not name.startswith("COM"):
        return port_name
    try:
        n = int(name[3:])
    except ValueError:
        return port_name
    if n >= 10:
        return r"\\.\%s" % name
    return port_name


def try_ports(
    ports=None,
    sampling_rate=1000,
    n_samples=10,
    analog_channels=None,
    serial_timeout=1.0,
    open_hard_timeout=5.0,
):
    if ports is None:
        ports = ["COM%d" % n for n in range(13, 17)]
    if analog_channels is None:
        analog_channels = [0, 1, 2]

    def probe_one(raw_port, device_port, result):
        b = BITalino()
        try:
            result["open_return"] = b.open(
                device_port,
                SamplingRate=sampling_rate,
                serial_timeout=serial_timeout,
            )
            if result["open_return"] == -1:
                return
            b.start(analogChannels=analog_channels)
            data = b.read(nSamples=n_samples)
            result["ok"] = True
            result["data_shape"] = getattr(data, "shape", "?")
            try:
                result["first_col"] = data[:, 0]
            except Exception:
                result["first_col"] = "?"
            try:
                b.stop()
            except Exception:
                pass
            try:
                b.close()
            except Exception:
                pass
        except Exception as ex:
            result["error"] = str(ex)
            try:
                b.stop()
            except Exception:
                pass
            try:
                b.close()
            except Exception:
                pass

    for raw in ports:
        device = windows_serial_device(raw)
        print(
            "Trying %s (device=%r, hard_timeout=%ss) ..."
            % (raw, device, open_hard_timeout),
            flush=True,
        )

        result = {"ok": False, "open_return": None, "error": None}
        t = threading.Thread(target=probe_one, args=(raw, device, result), daemon=True)
        t.start()
        t.join(open_hard_timeout)

        if t.is_alive():
            print(
                "  timed out (open/read blocked). Skipping %s." % raw,
                flush=True,
            )
            continue

        if result.get("error"):
            print("  failed: %s" % result["error"], flush=True)
            continue

        if result.get("open_return") == -1:
            print("  open() returned -1", flush=True)
            continue

        if result.get("ok"):
            print(
                "  OK: acquired %s samples, array shape %s"
                % (n_samples, result.get("data_shape", "?")),
                flush=True,
            )
            print("  First sample column: %s" % (result.get("first_col"),), flush=True)
            print(
                "Working port: %s - use this string as macAddress in BITalino.open()."
                % raw,
                flush=True,
            )
            return raw

    print("No BITalino found on any of: %s" % ports, flush=True)
    return None


if __name__ == "__main__":
    try_ports()
