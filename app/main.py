import multiprocessing
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent
QML = AKAR / "ui" / "qml" / "Main.qml"
DATA = AKAR.parent / "data"
MODEL = AKAR.parent / "models"


def lokasi_data(akar_aplikasi):
    """`lokasi-data.txt` di samping aplikasi mengarahkan data ke tempat lain, mis. volume VeraCrypt."""
    p = akar_aplikasi / "lokasi-data.txt"
    if p.exists():
        return Path(p.read_text(encoding="utf-8").strip())
    return akar_aplikasi / "data"


def buat_mesin_qml(data=DATA, mulai_wajah=True, muat_awal=False):
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from ui.bridge.alat import Alat
    from ui.bridge.bingkai import Bingkai
    from ui.bridge.cari import Cari
    from ui.bridge.folder import Folder
    from ui.bridge.galeri import Galeri
    from ui.bridge.orang import Orang, PenyediaWajah
    from ui.bridge.pengaturan import Pengaturan
    from ui.bridge.pindai import Pindai

    # Gaya Basic: gaya Windows bawaan menolak latar kontrol yang diganti
    if QQuickStyle.name() != "Basic":
        QQuickStyle.setStyle("Basic")
    jalur_db, akar_thumb = data / "library.db", data / "thumbs"
    pengaturan = Pengaturan(data / "pengaturan.json")
    galeri = Galeri(jalur_db, akar_thumb, pengaturan.tinggiBaris, muat_awal=muat_awal)
    det, rec = MODEL / "buffalo_l/det_10g.onnx", MODEL / "buffalo_l/w600k_r50.onnx"
    model = (str(det), str(rec), 4, str(data / "cache_mesin")) if det.exists() and rec.exists() and mulai_wajah else None
    pindai = Pindai(jalur_db, akar_thumb, galeri, model=model, jeda_baterai=lambda: pengaturan.jedaBaterai)
    orang = Orang(jalur_db, mulai=model is not None)
    # Satu foto contoh: ONNX Runtime siap lebih cepat daripada memuat kartu grafis
    cari = Cari(jalur_db, akar_thumb, model=(*model[:3], None, "ort") if model else None)
    pindai.perluKelompok.connect(orang.perbarui)
    pindai.sumberBerubah.connect(orang.segarkan)

    mesin = QQmlApplicationEngine()
    konteks = mesin.rootContext()
    konteks.setContextProperty("galeri", galeri)
    konteks.setContextProperty("pindai", pindai)
    konteks.setContextProperty("pengaturan", pengaturan)
    konteks.setContextProperty("orang", orang)
    konteks.setContextProperty("cari", cari)
    folder = Folder(jalur_db, akar_thumb, muat=False)  # Folder.qml memanggil segarkan saat dibuka
    pindai.sumberBerubah.connect(folder.segarkan)
    konteks.setContextProperty("folder", folder)
    mesin._folder = folder
    alat = Alat(data, galeri)
    konteks.setContextProperty("alat", alat)
    bingkai = Bingkai()
    konteks.setContextProperty("bingkai", bingkai)
    mesin._bingkai = bingkai
    mesin.addImageProvider("wajah", PenyediaWajah(akar_thumb))
    mesin._jembatan = (galeri, pindai, pengaturan, orang, cari, alat)  # QML tidak memegang rujukan Python
    mesin.load(QML.as_uri())
    if mesin.rootObjects():
        win = mesin.rootObjects()[0]
        bingkai.pasang(win)  # gaya jendela harus sudah benar sebelum tampil pertama
        win.show()
    return mesin


def _pesan(teks):
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, teks, "Recognice", 0x10)


def _uji_kemasan(data):
    """`--uji`: QML terbuka dan model termuat di proses pekerja, lalu tulis hasil dan keluar."""
    from concurrent.futures import ProcessPoolExecutor

    from core import pipa_wajah

    m = MODEL / "buffalo_l"
    with ProcessPoolExecutor(1, initializer=pipa_wajah.muat, initargs=(str(m / "det_10g.onnx"), str(m / "w600k_r50.onnx"), 1, str(data / "cache_mesin"))) as p:
        mesin = p.submit(pipa_wajah.siap).result()
    (data / "uji-kemas.txt").write_text(f"ok {mesin}", encoding="utf-8")


def main():
    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtGui import QGuiApplication, QIcon

    from core import cadangan

    data = lokasi_data(AKAR.parent)
    data.mkdir(parents=True, exist_ok=True)
    kunci = QLockFile(str(data / "aplikasi.lock"))
    kunci.setStaleLockTime(0)
    if not kunci.tryLock(0):
        _pesan("Recognice sudah terbuka.")  # dua pemindai pada satu database saling mengganggu
        return 0
    try:
        cadangan.terapkan_bila_ada(data)
        app = QGuiApplication(sys.argv)
        app.setApplicationName("Recognice")
        app.setWindowIcon(QIcon(str(AKAR / "ui" / "qml" / "ikon.svg")))
        uji = "--uji" in sys.argv
        mesin = buat_mesin_qml(data, mulai_wajah=not uji)
        if not mesin.rootObjects():
            raise RuntimeError("Antarmuka gagal dimuat.")
        if uji:
            QTimer.singleShot(500, lambda: (_uji_kemasan(data), app.quit()))
        return app.exec()
    except Exception:
        import traceback

        (data / "galat_mulai.txt").write_text(traceback.format_exc(), encoding="utf-8")
        _pesan(f"Recognice gagal dibuka. Rincian ada di {data / 'galat_mulai.txt'}")
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
