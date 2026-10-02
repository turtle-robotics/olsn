# -*- coding: utf-8 -*-
"""
Stream EMG (analog) samples from a BITalino serial/COM port to the terminal.

Uses short read() chunks so values appear in near real time. Default port COM15;
default analog channels 1-4. Each line prints elapsed time, sample count, then
last raw sample per channel as a comma-separated list (BITalino row order).

Run (from this folder):
  python stream_emg_terminal.py
  python stream_emg_terminal.py --port COM15 --chunk 40 --rate 1000

Stop with Ctrl+C.
"""

import argparse
import os
import signal
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from bitalino import BITalino


def windows_serial_device(port_name):
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


def main():
    p = argparse.ArgumentParser(description="Stream BITalino EMG to terminal")
    p.add_argument("--port", default="COM15", help="Serial port (default COM15)")
    p.add_argument(
        "--rate",
        type=int,
        default=1000,
        choices=(1, 10, 100, 1000),
        help="Sampling rate in Hz (default 1000)",
    )
    p.add_argument(
        "--channels",
        default="1,2,3,4",
        help="Comma-separated analog indices 0-5 (default 1,2,3,4)",
    )
    p.add_argument(
        "--chunk",
        type=int,
        default=50,
        help="Samples per read(); smaller = more frequent updates (default 50)",
    )
    args = p.parse_args()

    analog = [int(x.strip()) for x in args.channels.split(",") if x.strip()]
    for c in analog:
        if c not in range(6):
            p.error("channel %s not in 0..5" % c)

    analog_order = sorted(analog)
    n_emg = len(analog_order)

    device = windows_serial_device(args.port)
    b = BITalino()
    stop = {"flag": False}

    def on_sigint(_sig, _frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, on_sigint)

    if b.open(device, SamplingRate=args.rate) == -1:
        print("Failed to open %s" % device, file=sys.stderr)
        sys.exit(1)

    try:
        b.start(analogChannels=analog_order)
    except Exception as ex:
        print("start() failed: %s" % ex, file=sys.stderr)
        b.close()
        sys.exit(1)

    header = "elapsed_s,n_samples,%s" % ",".join(
        "ch%d" % c for c in analog_order
    )
    print(
        "Streaming port=%s rate=%dHz chunk=%d analog=%s (raw counts). Ctrl+C to stop."
        % (args.port, args.rate, args.chunk, analog_order),
        flush=True,
    )
    print(header, flush=True)

    t0 = time.perf_counter()
    n_total = 0

    try:
        while not stop["flag"]:
            data = b.read(nSamples=args.chunk)
            n_total += data.shape[1]
            elapsed = time.perf_counter() - t0
            lasts = [
                "%.1f" % float(data[5 + i, -1]) for i in range(n_emg)
            ]
            print(
                "%.3f,%d,%s"
                % (elapsed, n_total, ",".join(lasts)),
                flush=True,
            )
    except KeyboardInterrupt:
        pass
    finally:
        try:
            b.stop()
        except Exception:
            pass
        try:
            b.close()
        except Exception:
            pass
        print("Stopped.", flush=True)


if __name__ == "__main__":
    main()
