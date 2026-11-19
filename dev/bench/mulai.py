"""Waktu buka aplikasi pada pustaka nyata: dari proses mulai sampai frame pertama."""
import sys
import time

t0 = time.perf_counter()
from pathlib import Path  # noqa: E402

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401

import main as aplikasi  # noqa: E402

t1 = time.perf_counter()
app = QGuiApplication(sys.argv)
mesin = aplikasi.buat_mesin_qml(AKAR / "data", mulai_wajah=False)
t2 = time.perf_counter()
win = mesin.rootObjects()[0]
galeri = mesin._jembatan[0]
sudah = []


def frame():
    if not sudah:
        sudah.append(time.perf_counter())
        QTimer.singleShot(0, selesai)


def selesai():
    a = time.perf_counter()
    galeri.muatUlang()
    b = time.perf_counter()
    print(f"impor {t1 - t0:.2f} s; mesin+QML+DB {t2 - t1:.2f} s; frame pertama {sudah[0] - t0:.2f} s; "
          f"muatUlang {b - a:.3f} s; {galeri.jumlah} foto", flush=True)
    app.quit()


win.frameSwapped.connect(frame)
QTimer.singleShot(20000, app.quit)
sys.exit(app.exec())
