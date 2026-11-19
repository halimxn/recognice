"""Rincian waktu buka aplikasi pada pustaka nyata: impor, tiap jembatan, QML, frame pertama.

    .venv\\Scripts\\python.exe dev\\bench\\mulai_rinci.py
"""
import sys
import time

t0 = time.perf_counter()
from pathlib import Path  # noqa: E402

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401

t_qt = time.perf_counter()
import main as aplikasi  # noqa: E402
from ui.bridge import folder, galeri, orang, pindai  # noqa: E402

catatan = {}


def ukur(kelas, nama):
    asli = kelas.__init__

    def baru(self, *a, **k):
        t = time.perf_counter()
        asli(self, *a, **k)
        catatan[nama] = catatan.get(nama, 0) + time.perf_counter() - t

    kelas.__init__ = baru


for k, n in ((galeri.Galeri, "Galeri"), (folder.Folder, "Folder"), (orang.Orang, "Orang"), (pindai.Pindai, "Pindai")):
    ukur(k, n)
t1 = time.perf_counter()
app = QGuiApplication(sys.argv)
mesin = aplikasi.buat_mesin_qml(AKAR / "data", mulai_wajah=False)
t2 = time.perf_counter()
win = mesin.rootObjects()[0]
g = mesin._jembatan[0]
sudah = []


def frame():
    if not sudah:
        sudah.append(time.perf_counter())
        QTimer.singleShot(400, selesai)


def selesai():
    print(f"impor Qt {t_qt - t0:.2f} s, impor aplikasi {t1 - t_qt:.2f} s, buat mesin {t2 - t1:.2f} s "
          f"(" + ", ".join(f"{k} {v:.2f}" for k, v in catatan.items()) + f"), frame pertama {sudah[0] - t0:.2f} s, "
          f"galeri terisi {g.jumlah} foto", flush=True)
    a = time.perf_counter()
    g.muatUlang()
    print(f"muatUlang galeri {time.perf_counter() - a:.3f} s", flush=True)
    app.quit()


win.frameSwapped.connect(frame)
QTimer.singleShot(20000, app.quit)
sys.exit(app.exec())
