"""FPS galeri asli pada pustaka nyata (hanya angka; tidak menyimpan gambar)."""
import statistics as st
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
sys.path.insert(0, str(AKAR / "dev/bench"))

import numpy as np  # noqa: E402
from PySide6.QtCore import QObject, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401

import main as aplikasi  # noqa: E402
from ui_grid import ram_mb  # noqa: E402

t0 = time.perf_counter()
app = QGuiApplication(sys.argv)
mesin = aplikasi.buat_mesin_qml(AKAR / "data", mulai_wajah=False, muat_awal=True)
win = mesin.rootObjects()[0]
daftar = win.findChild(QObject, "daftar")
galeri = mesin._jembatan[0]
waktu = []
win.frameSwapped.connect(lambda: waktu.append(time.perf_counter()))
FASE = [("diam", 0, 3.0), ("gulir", 2000, 12.0), ("scrub", 30000, 8.0), ("mendarat", 0, 2.0)]
tik = QTimer(interval=16)


def lapor(nama):
    if len(waktu) < 8:
        print(nama, "tidak ada frame (layar tidak berubah)", flush=True)
        waktu.clear()
        return
    w = np.diff(np.array(waktu)) * 1000
    w = w[3:]
    ram, puncak = ram_mb()
    print(f"{nama:8} frame {len(w):5d} fps {1000 / w.mean():5.1f} median {st.median(w):5.1f} ms p95 {np.percentile(w, 95):5.1f} "
          f"p99 {np.percentile(w, 99):5.1f} maks {w.max():6.1f} RAM {ram:.0f} MB (puncak {puncak:.0f})", flush=True)
    waktu.clear()


i = -1
akhir = 0.0
kec = 0
terakhir = 0.0


def langkah():
    global i, akhir, kec, terakhir
    now = time.perf_counter()
    if now >= akhir:
        if i >= 0:
            lapor(FASE[i][0])
        i += 1
        if i == len(FASE):
            tik.stop()
            app.quit()
            return
        kec, dur = FASE[i][1], FASE[i][2]
        akhir, terakhir = now + dur, now
        waktu.clear()
        return
    if kec:
        daftar.setProperty("contentY", min(daftar.property("contentY") + kec * (now - terakhir),
                                           galeri.tinggiTotal - daftar.property("height")))
    terakhir = now


def mulai():
    print(f"tampil: {time.perf_counter() - t0:.2f} s; {galeri.jumlah} foto; tinggi {galeri.tinggiTotal}; exposed {win.isExposed()}; lebar {daftar.property('width')}", flush=True)
    tik.timeout.connect(langkah)
    tik.start()


QTimer.singleShot(1500, mulai)
sys.exit(app.exec())
