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
from collections import deque

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


def load_activation_scores(path):
    scores = {}
    current = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("["):
                    continue
                if ":" not in line:
                    current = line
                    scores[current] = {}
                    continue
                if current is None:
                    continue
                left, right = line.split(":", 1)
                try:
                    ch = int(left.strip())
                    val = float(right.strip())
                except ValueError:
                    continue
                scores[current][ch] = val
    except OSError:
        pass
    return scores


class GestureClassifier(object):
    def __init__(self, gesture_scores):
        self._gesture_scores = gesture_scores or {
            "Extension": {0: 5, 1: 5, 2: 3, 3: 1},
            "Flexion": {0: 1, 1: 1, 2: 1, 3: 5},
            "Radial Deviation": {0: 2, 1: 4, 2: 1, 3: 1},
            "Ulnar Deviation": {0: 2, 1: 2, 2: 3, 3: 3},
            "Splay": {0: 4, 1: 4, 2: 1, 3: 2},
            "Rest": {0: 1, 1: 1, 2: 1, 3: 1},
        }
        self._baseline = 500.0
        self._small_thr = 35.0
        self._medium_thr = 120.0
        self._big_thr = 220.0
        self._alpha = 0.2
        self._smoothed_dev = np.zeros(4, dtype=np.float64)
        self._active = np.zeros(4, dtype=bool)
        self._candidate = "Rest"
        self._stable_label = "Rest"
        self._candidate_count = 0
        self._persist_needed = 3
        self._rest_candidate_count = 0
        self._rest_persist_needed = 3
        self._latest_scores = {}
        self._min_non_rest_confidence = 0.10
        self._templates = self._build_templates(self._gesture_scores)

    @staticmethod
    def _safe_channel_values(values):
        out = np.zeros(4, dtype=np.float64)
        n = min(4, len(values))
        if n > 0:
            out[:n] = np.asarray(values[:n], dtype=np.float64)
        return out

    def _weighted_gesture_scores(self, level):
        gesture_vals = {}
        for gesture, mapping in self._gesture_scores.items():
            total = 0.0
            for ch in range(4):
                total += mapping.get(ch, 0.0) * level[ch]
            gesture_vals[gesture] = total
        return gesture_vals

    @staticmethod
    def _cosine_similarity(a, b):
        da = float(np.linalg.norm(a))
        db = float(np.linalg.norm(b))
        if da <= 1e-9 or db <= 1e-9:
            return 0.0
        return float(np.dot(a, b) / (da * db))

    def _build_templates(self, gesture_scores):
        templates = {}
        for gesture, mapping in gesture_scores.items():
            if gesture == "Rest":
                continue
            vec = np.array([float(mapping.get(ch, 0.0)) for ch in range(4)], dtype=np.float64)
            s = float(np.sum(vec))
            if s > 1e-9:
                vec = vec / s
            templates[gesture] = vec
        return templates

    def update_from_chunk(self, emg_by_channel):
        if emg_by_channel.size == 0:
            return self._stable_label, self._latest_scores, self._smoothed_dev.copy()

        # Robust to spikes/noise: use percentile deviation over short chunk, then smooth over time.
        dev = np.abs(emg_by_channel - self._baseline)
        p90 = np.percentile(dev, 90, axis=1)
        p90_4 = self._safe_channel_values(p90)
        self._smoothed_dev = (1.0 - self._alpha) * self._smoothed_dev + self._alpha * p90_4

        level = np.clip((self._smoothed_dev - self._small_thr) / (self._big_thr - self._small_thr), 0.0, 1.0)
        active = self._smoothed_dev >= self._small_thr
        medium = self._smoothed_dev >= self._medium_thr
        big = self._smoothed_dev >= self._big_thr
        low = self._smoothed_dev < (0.8 * self._small_thr)
        self._active = active

        if not np.any(active):
            raw_label = "Rest"
            gesture_vals = self._weighted_gesture_scores(level)
            gesture_vals["Rest"] = gesture_vals.get("Rest", 0.0)
            self._latest_scores = gesture_vals
        else:
            # Base weighted vote from activation score profiles.
            gesture_vals = self._weighted_gesture_scores(level)
            # If any activation exists, bias away from Rest.
            gesture_vals["Rest"] = gesture_vals.get("Rest", 0.0) * 0.45

            l0, l1, l2, l3 = [float(x) for x in level]
            profile_sum = float(np.sum(level))
            if profile_sum > 1e-9:
                profile = level / profile_sum
            else:
                profile = level.copy()

            # Add profile similarity term so "shape across channels" can beat
            # broad amplitude-dominant classes like extension/flexion.
            for gesture, template in self._templates.items():
                sim = self._cosine_similarity(profile, template)
                # Similarity becomes more important once there is meaningful signal.
                gesture_vals[gesture] = gesture_vals.get(gesture, 0.0) + (2.8 * sim + 0.7 * sim * profile_sum)

            pattern_boost = {
                "Extension": 0.0,
                "Flexion": 0.0,
                "Radial Deviation": 0.0,
                "Ulnar Deviation": 0.0,
                "Splay": 0.0,
            }

            # Extension/Flexion require clearer dominance so they don't mask finer classes.
            if medium[0] and medium[1] and medium[2]:
                pattern_boost["Extension"] += max(0.0, (l0 + l1 + l2) / 3.0 - 0.65 * l3) * 2.2
            if medium[3]:
                pattern_boost["Flexion"] += max(0.0, l3 - 0.55 * max(l0, l1, l2)) * 2.2

            # Extension rescue: if 0-2 are clearly active and 3 is comparatively low,
            # give extension a strong but specific lift.
            extension_signature = (
                l0 >= 0.26 and l1 >= 0.26 and l2 >= 0.20 and
                l3 <= 0.22 and
                (l0 + l1 + l2) >= 0.95
            )
            if extension_signature:
                pattern_boost["Extension"] += 2.9 + 1.1 * (l0 + l1 + l2 - l3)

            # Radial: ch1 strongest, ch0 moderate, ch2/ch3 low.
            radial_core = (1.25 * l1 + 0.8 * l0) - (0.85 * l2 + 0.85 * l3)
            if l1 >= 0.24 and l0 >= 0.12 and low[2] and low[3]:
                pattern_boost["Radial Deviation"] += max(0.0, radial_core) * 2.6

            # Splay: ch0/ch1 high with some ch3, and low ch2.
            splay_core = (l0 + l1 + 0.55 * l3) - (1.1 * l2)
            if l0 >= 0.24 and l1 >= 0.24 and l3 >= 0.05 and low[2]:
                pattern_boost["Splay"] += max(0.0, splay_core) * 2.4

            # Ulnar: ch2/ch3 elevated together, weaker ch0/ch1.
            ulnar_core = (0.95 * l2 + 0.95 * l3 + 0.35 * l1) - (0.65 * l0)
            if l2 >= 0.14 and l3 >= 0.14:
                pattern_boost["Ulnar Deviation"] += max(0.0, ulnar_core) * 2.2

            # Extra promotion for under-selected classes.
            if "Radial Deviation" in pattern_boost:
                pattern_boost["Radial Deviation"] *= 1.95
            if "Ulnar Deviation" in pattern_boost:
                pattern_boost["Ulnar Deviation"] *= 1.8
            if "Splay" in pattern_boost:
                pattern_boost["Splay"] *= 1.9

            for name, boost in pattern_boost.items():
                if name in gesture_vals:
                    gesture_vals[name] += boost

            # Penalize extension/flexion when their "other channels low" assumptions fail.
            if "Extension" in gesture_vals:
                ext_penalty = max(0.0, l3 - 0.22) * 3.0
                gesture_vals["Extension"] -= ext_penalty
            if "Flexion" in gesture_vals:
                flex_penalty = max(0.0, max(l0, l1, l2) - 0.28) * 2.8
                gesture_vals["Flexion"] -= flex_penalty

            # More suppression when profile strongly matches non-ext/flex templates.
            ext_like = (0.45 * l0 + 0.45 * l1 + 0.35 * l2) - (0.95 * l3)
            flex_like = (1.1 * l3) - (0.35 * l0 + 0.35 * l1 + 0.35 * l2)
            fine_like = max(
                1.25 * l1 + 0.9 * l0 - 0.9 * l2 - 0.9 * l3,  # radial-like
                1.0 * l2 + 1.0 * l3 - 0.7 * l0 - 0.4 * l1,   # ulnar-like
                1.0 * l0 + 1.0 * l1 + 0.55 * l3 - 1.2 * l2,  # splay-like
            )
            if fine_like > max(ext_like, flex_like):
                if "Extension" in gesture_vals:
                    gesture_vals["Extension"] *= 0.84
                if "Flexion" in gesture_vals:
                    gesture_vals["Flexion"] *= 0.72

            # If extension shape is dominant, undo some anti-ext suppression.
            if extension_signature and "Extension" in gesture_vals:
                gesture_vals["Extension"] += 1.8

            # Clamp to non-negative for readability in UI.
            for k in list(gesture_vals.keys()):
                gesture_vals[k] = max(0.0, float(gesture_vals[k]))

            raw_label = max(gesture_vals, key=gesture_vals.get)
            non_rest_best = max(
                (v for k, v in gesture_vals.items() if k != "Rest"),
                default=0.0,
            )
            if raw_label != "Rest" and non_rest_best < self._min_non_rest_confidence:
                raw_label = "Rest"
            self._latest_scores = gesture_vals

        # Latching behavior:
        # - While in Rest: allow normal transition to any gesture (with persistence).
        # - While in a gesture: keep that gesture latched until Rest is stable.
        if self._stable_label != "Rest":
            if raw_label == "Rest":
                self._rest_candidate_count += 1
            else:
                self._rest_candidate_count = 0

            if self._rest_candidate_count >= self._rest_persist_needed:
                self._stable_label = "Rest"
                self._candidate = "Rest"
                self._candidate_count = self._rest_candidate_count
                self._rest_candidate_count = 0
        else:
            if raw_label == self._candidate:
                self._candidate_count += 1
            else:
                self._candidate = raw_label
                self._candidate_count = 1

            if self._candidate_count >= self._persist_needed:
                self._stable_label = self._candidate
                self._rest_candidate_count = 0

        return self._stable_label, dict(self._latest_scores), self._smoothed_dev.copy()


class GestureWindow(QtWidgets.QMainWindow):
    def __init__(self, gesture_names):
        super(GestureWindow, self).__init__()
        self.setWindowTitle("EMG Gesture Classification")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._gesture_label = QtWidgets.QLabel("Gesture: Rest")
        f = self._gesture_label.font()
        f.setPointSize(max(12, f.pointSize() + 2))
        f.setBold(True)
        self._gesture_label.setFont(f)
        layout.addWidget(self._gesture_label)

        self._channels_label = QtWidgets.QLabel("Channel activity: ch0=0 ch1=0 ch2=0 ch3=0")
        layout.addWidget(self._channels_label)

        self._score_labels = {}
        for name in gesture_names:
            lbl = QtWidgets.QLabel("%s: 0.000" % name)
            self._score_labels[name] = lbl
            layout.addWidget(lbl)

    def update_view(self, gesture, scores, smoothed_dev):
        self._gesture_label.setText("Gesture: %s" % gesture)
        self._channels_label.setText(
            "Channel activity: ch0=%.1f ch1=%.1f ch2=%.1f ch3=%.1f"
            % (smoothed_dev[0], smoothed_dev[1], smoothed_dev[2], smoothed_dev[3])
        )
        for name, lbl in self._score_labels.items():
            lbl.setText("%s: %.3f" % (name, float(scores.get(name, 0.0))))


class EMGWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        device,
        analog_order,
        rate_hz,
        chunk,
        window_s,
        serial_timeout,
        classifier=None,
        classifier_window=None,
    ):
        super(EMGWindow, self).__init__()
        self.setWindowTitle("BITalino EMG — port %s @ %d Hz" % (device, rate_hz))

        self._analog_order = analog_order
        self._rate_hz = float(rate_hz)
        self._chunk = int(chunk)
        self._dt = 1.0 / self._rate_hz
        self._device = device
        self._serial_timeout = serial_timeout
        self._classifier = classifier
        self._classifier_window = classifier_window

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
        emg_rows = []
        for i in range(n_emg):
            row = 5 + i
            row_vals = data[row, :]
            self._ys[i].extend(row_vals.tolist())
            emg_rows.append(row_vals)

        if self._classifier is not None and self._classifier_window is not None and emg_rows:
            emg_mat = np.asarray(emg_rows, dtype=np.float64)
            gesture, scores, smoothed_dev = self._classifier.update_from_chunk(emg_mat)
            self._classifier_window.update_view(gesture, scores, smoothed_dev)

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
    score_path = os.path.join(SCRIPT_DIR, "activation_scores.txt")
    gesture_scores = load_activation_scores(score_path)
    classifier = GestureClassifier(gesture_scores=gesture_scores)
    gesture_names = list(gesture_scores.keys()) if gesture_scores else [
        "Extension",
        "Flexion",
        "Radial Deviation",
        "Ulnar Deviation",
        "Splay",
        "Rest",
    ]

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    gesture_win = GestureWindow(gesture_names=gesture_names)
    win = EMGWindow(
        device=device,
        analog_order=analog_order,
        rate_hz=args.rate,
        chunk=args.chunk,
        window_s=args.window,
        serial_timeout=args.serial_timeout,
        classifier=classifier,
        classifier_window=gesture_win,
    )
    win.resize(900, 200 + 160 * len(analog_order))
    gesture_win.resize(420, 280)
    win.show()
    gesture_win.show()
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())


if __name__ == "__main__":
    main()