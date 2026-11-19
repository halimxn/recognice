"""Prototipe grid QML 20.000 thumbnail: ukur waktu frame saat gulir dan RAM. Thumbnail sintetis, bukan foto pemilik."""
import ctypes
import json
import os
import statistics as st
import sys
import time
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image

KELUAR = Path(__file__).parent / "out"
THUMB = KELUAR / "thumbs"
N = 20000


def buat_thumbnail():
    if (THUMB / f"{(N - 1) % 256:02x}" / f"{N - 1}.jpg").exists():
        return
    acak = np.random.default_rng(1)
    t0 = time.perf_counter()
    for i in range(N):
        d = THUMB / f"{i % 256:02x}"
        d.mkdir(parents=True, exist_ok=True)
        kasar = acak.integers(0, 255, (11, 16, 3), dtype=np.uint8)
        im = Image.fromarray(kasar).resize((256, 170), Image.Resampling.BILINEAR)
        im.save(d / f"{i}.jpg", "JPEG", quality=78)
    print(f"thumbnail sintetis dibuat: {time.perf_counter() - t0:.0f} s")


class Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (n, ctypes.c_size_t) for n in ("Peak", "WorkingSet", "a", "b", "c", "d", "e", "f")]


def ram_mb():
    c = Counters()
    c.cb = ctypes.sizeof(c)
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.WorkingSet / 1e6, c.Peak / 1e6


def main():
    buat_thumbnail()
    os.environ["QSG_INFO"] = "1"
    from PySide6.QtCore import QObject, QTimer, QUrl, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    app = QGuiApplication(sys.argv)

    class Lapor(QObject):
        @Slot(str, str)
        def fase(self, nama, data):
            w = np.diff(np.array(json.loads(data), float))[5:]  # jam dinding; frame awal memuat delegasi pertama
            ram, puncak = ram_mb()
            print(f"{nama:8} frame {len(w):5d}  fps {1000 / w.mean():5.1f}  median {st.median(w):5.1f} ms  "
                  f"p95 {np.percentile(w, 95):5.1f} ms  p99 {np.percentile(w, 99):5.1f} ms  "
                  f"RAM {ram:.0f} MB (puncak {puncak:.0f})", flush=True)

        @Slot()
        def selesai(self):
            QTimer.singleShot(200, app.quit)

    lapor = Lapor()
    mesin = QQmlApplicationEngine()
    mesin.rootContext().setContextProperty("lapor", lapor)
    mesin.rootContext().setContextProperty("akarThumb", THUMB.as_uri())
    mesin.rootContext().setContextProperty("keluar", str(KELUAR).replace("\\", "/"))
    mesin.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui_grid.qml")))
    if not mesin.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
