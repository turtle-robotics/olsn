# -*- coding: utf-8 -*-
"""
Real-time BITalino EMG in one window: one pyqtgraph panel per analog channel.

Run from this folder:
  pip install pyqtgraph PySide6
  python stream_emg_pyqtgraph.py
  python stream_emg_pyqtgraph.py --port COM15 --channels 0,1,2 --window 2.0

Close the window to stop acquisition and release the serial port.
"""

from __future__ import print_function

import argparse
import os
import queue
import sys
import threading

import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

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


class EMGWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        device,
        analog_order,
        rate_hz,
        chunk,
        window_s,
        serial_timeout,
    ):
        super(EMGWindow, self).__init__()
        self.setWindowTitle("BITalino EMG — port %s @ %d Hz" % (device, rate_hz))

        self._analog_order = analog_order
        self._rate_hz = float(rate_hz)
        self._chunk = int(chunk)
        self._dt = 1.0 / self._rate_hz
        self._device = device
        self._serial_timeout = serial_timeout

        max_points = max(100, int(window_s * rate_hz) + self._chunk)
        self._t = deque_maxlen(max_points)
        self._ys = [deque_maxlen(max_points) for _ in analog_order]

        self._data_queue = queue.Queue(maxsize=32)
        self._stop = threading.Event()
        self._b = BITalino()
        self._reader_thread = None
        self._reader_error = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        pg.setConfigOptions(antialias=True)
        self._plots = []
        self._curves = []
        first_pw = None
        for ch in analog_order:
            pw = pg.PlotWidget(title="Analog channel %d (raw counts)" % ch)
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel("left", "counts")
            pw.setLabel("bottom", "time (s)")
            # Fixed vertical scale (10-bit counts); avoid auto-range on each setData().
            vb = pw.getViewBox()
            vb.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
            vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
            pw.setYRange(0, 1023, padding=0)
            if first_pw is None:
                first_pw = pw
            else:
                pw.setXLink(first_pw)
            pen = pg.mkPen(width=1)
            curve = pw.plot(pen=pen)
            curve.setClipToView(True)
            self._plots.append(pw)
            self._curves.append(curve)
            layout.addWidget(pw, stretch=1)

        self._status = QtWidgets.QLabel("Connecting…")
        layout.addWidget(self._status, stretch=0)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start(15)

        self._open_and_start_reader()

    def _open_and_start_reader(self):
        if self._b.open(
            self._device,
            SamplingRate=int(self._rate_hz),
            serial_timeout=self._serial_timeout,
        ) == -1:
            self._status.setText("Failed to open %s" % self._device)
            return
        try:
            self._b.start(analogChannels=list(self._analog_order))
        except Exception as ex:
            self._status.setText("start() failed: %s" % ex)
            try:
                self._b.close()
            except Exception:
                pass
            return

        self._status.setText(
            "Streaming %s — channels %s — close window to stop."
            % (self._device, list(self._analog_order))
        )

        def read_loop():
            t_accum = 0.0
            b = self._b
            ch = self._chunk
            dt = self._dt
            q = self._data_queue
            stop = self._stop
            while not stop.is_set():
                try:
                    data = b.read(nSamples=ch)
                except Exception as ex:
                    self._reader_error = ex
                    break
                n = data.shape[1]
                t_chunk = t_accum + np.arange(n, dtype=np.float64) * dt
                t_accum += n * dt
                try:
                    q.put_nowait((t_chunk, np.asarray(data, dtype=np.float64)))
                except queue.Full:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        q.put_nowait((t_chunk, np.asarray(data, dtype=np.float64)))
                    except queue.Full:
                        pass

        self._reader_thread = threading.Thread(target=read_loop, name="bitalino-read")
        self._reader_thread.daemon = True
        self._reader_thread.start()

    def _append_chunk(self, t_chunk, data):
        n_emg = len(self._analog_order)
        self._t.extend(t_chunk.tolist())
        for i in range(n_emg):
            row = 5 + i
            self._ys[i].extend(data[row, :].tolist())

    def _on_timer(self):
        if self._reader_error is not None:
            self._status.setText("Read error: %s" % self._reader_error)
            self._reader_error = None
            self._timer.stop()
            return

        updated = False
        while True:
            try:
                t_chunk, data = self._data_queue.get_nowait()
            except queue.Empty:
                break
            self._append_chunk(t_chunk, data)
            updated = True

        if not updated:
            return

        t_list = list(self._t)
        for i, curve in enumerate(self._curves):
            curve.setData(t_list, list(self._ys[i]), connect="finite")

    def closeEvent(self, event):
        self._stop.set()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2.0)
        try:
            self._b.stop()
        except Exception:
            pass
        try:
            self._b.close()
        except Exception:
            pass
        super(EMGWindow, self).closeEvent(event)


def deque_maxlen(n):
    from collections import deque

    return deque(maxlen=n)


def main():
    p = argparse.ArgumentParser(description="BITalino EMG real-time plots (pyqtgraph)")
    p.add_argument("--port", default="COM15", help="Serial port (default COM15)")
    p.add_argument(
        "--rate",
        type=int,
        default=1000,
        choices=(1, 10, 100, 1000),
        help="Sampling rate Hz (default 1000)",
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
        help="Samples per read(); smaller = snappier UI load (default 50)",
    )
    p.add_argument(
        "--window",
        type=float,
        default=2.0,
        help="Visible history in seconds (default 2.0)",
    )
    p.add_argument(
        "--serial-timeout",
        type=float,
        default=1.0,
        help="pySerial read timeout in seconds (default 1.0)",
    )
    args = p.parse_args()

    analog = [int(x.strip()) for x in args.channels.split(",") if x.strip()]
    for c in analog:
        if c not in range(6):
            p.error("channel %s not in 0..5" % c)

    analog_order = sorted(analog)
    device = windows_serial_device(args.port)

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    win = EMGWindow(
        device=device,
        analog_order=analog_order,
        rate_hz=args.rate,
        chunk=args.chunk,
        window_s=args.window,
        serial_timeout=args.serial_timeout,
    )
    win.resize(900, 200 + 160 * len(analog_order))
    win.show()
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())


if __name__ == "__main__":
    main()
