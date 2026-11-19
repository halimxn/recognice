"""Pustaka sintetis lalu tangkapan layar tiap keadaan ke dev/uji/foto/. Bukan foto pemilik."""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
CONTOH = AKAR / "dev/uji/contoh"
KELUAR = AKAR / "dev/uji/foto"


def siapkan():
    from PIL import Image

    from core import db, library, scanner

    foto = CONTOH / "foto"
    data = CONTOH / "data"
    if (data / "library.db").exists():
        return data
    acak = random.Random(5)
    t = datetime(2026, 10, 20, 9)
    for i in range(420):
        if i % acak.randint(5, 14) == 0:
            t -= timedelta(days=acak.randint(1, 40))
        lb, tg = acak.choice([(1600, 1200), (1200, 1600), (1920, 1080), (1200, 1200), (2400, 800), (1200, 1500)])
        a, b = [acak.randint(30, 225) for _ in range(3)], [acak.randint(30, 225) for _ in range(3)]
        im = Image.linear_gradient("L").resize((lb, tg))
        im = Image.merge("RGB", [im.point(lambda v, p=a[k], q=b[k]: p + (q - p) * v // 255) for k in range(3)])
        ex = Image.Exif()
        ex.get_ifd(0x8769)[36867] = t.strftime("%Y:%m:%d %H:%M:%S")
        p = foto / f"{t.year}" / f"contoh_{i:04d}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        im.save(p, "JPEG", exif=ex, quality=80)
    c = db.buka(data / "library.db")
    sid = library.tambah_sumber(c, str(foto))
    print(scanner.Pemindai(c, data / "thumbs", pekerja=2).jalankan(sid))
    c.close()
    return data


def main():
    data = siapkan() if "--kosong" not in sys.argv else CONTOH / "kosong"
    from PySide6.QtCore import QMetaObject, QObject, QRectF, QTimer, Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickWindow  # noqa: F401  mengenalkan tipe jendela QML ke Python

    import main as aplikasi

    app = QGuiApplication(sys.argv)
    mesin = aplikasi.buat_mesin_qml(data, mulai_wajah=False, muat_awal=True)
    win = mesin.rootObjects()[0]
    win.setWidth(1366)
    win.setHeight(720)
    KELUAR.mkdir(exist_ok=True)
    lb = win.findChild(QObject, "lightbox")
    galeri, _, pengaturan, orang, cari, _alat = mesin._jembatan
    nama = "kosong" if "--kosong" in sys.argv else None

    def pura_pura_pindai():
        p = mesin._jembatan[1]
        p._aktif, p._kini, p._total, p._sumber_aktif = True, 1204, 21775, 1
        p.berubah.emit()

    def pura_pura_wajah():
        p = mesin._jembatan[1]
        p._aktif, p._tahap, p._kini, p._total = True, "wajah", 3120, 21692
        p.berubah.emit()

    def wajah_contoh():
        f = galeri.foto(12)["id"]
        with galeri._c:
            galeri._c.execute("DELETE FROM face")
            for x, y, w in ((0.15, 0.2, 0.25), (0.55, 0.35, 0.2)):
                galeri._c.execute(
                    "INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model) "
                    "VALUES (?,?,?,?,?,x'00',1,1,1,1,1,x'00','contoh')", (f, x, y, x + w, y + w * 0.8))

    hal = win.findChild(QObject, "orangHalaman")

    def orang_contoh():
        import numpy as np

        from core.pipa_wajah import MODEL as MODEL_CONTOH
        acak = np.random.default_rng(2)
        c = galeri._c
        ids = [b[0] for b in c.execute("SELECT id FROM photo ORDER BY id")]
        with c:
            c.execute("DELETE FROM face")
            c.execute("DELETE FROM person")
            k = 0
            for p in range(14):
                nama = ["Ayu", "Budi", "Citra", "Dewi", "Eko"][p] if p < 5 else None
                pid = c.execute("INSERT INTO person(nama, dibuat) VALUES (?,1)", (nama,)).lastrowid
                arah = acak.standard_normal(512)
                for j in range(30 - p * 2):
                    v = arah + acak.normal(0, 0.03 * 22, 512)
                    v = (v / np.linalg.norm(v)).astype(np.float16).tobytes()
                    c.execute("INSERT INTO face(photo_id,x1,y1,x2,y2,titik,skor,lebar_px,tajam,frontal,kualitas,embedding,model,person_id,state) "
                              "VALUES (?,0.3,0.3,0.6,0.6,x'00',1,120,300,1,?,?,?,?,'otomatis')", (ids[k % len(ids)], 0.9 - j * 0.01, v, MODEL_CONTOH, pid))
                    k += 1
        orang.segarkan()

    def selesai_pindai():
        p = mesin._jembatan[1]
        p._aktif, p._sumber_aktif = False, -1
        p.berubah.emit()

    def buka(i):
        lb.setProperty("indeks", i)
        QMetaObject.invokeMethod(lb, "muat", Qt.ConnectionType.DirectConnection)

    def filter_terbuka(v=True):
        win.findChild(QObject, "galeriHalaman").setProperty("filterTerbuka", v)

    langkah = ([lambda: None] if nama else [
        ("galeri_gelap", lambda: (win.setWidth(1130), win.setHeight(696), pengaturan.aturTema("gelap"))),
        ("folder_gelap", lambda: (win.setWidth(1366), win.setHeight(720), win.setProperty("menuAktif", 0))),
        ("folder_terang", lambda: pengaturan.aturTema("terang")),
        ("galeri_terang", lambda: win.setProperty("menuAktif", 1)),
        ("sumber_terang", lambda: win.setProperty("menuAktif", 4)),
        ("sumber_gelap", lambda: pengaturan.aturTema("gelap")),
        ("pengaturan", lambda: win.setProperty("menuAktif", 5)),
        ("memindai", lambda: (win.setProperty("menuAktif", 4), pura_pura_pindai())),
        ("sempit", lambda: (selesai_pindai(), win.setProperty("menuAktif", 1), win.setWidth(860))),
        ("lightbox", lambda: (win.setWidth(1366), lb.setProperty("infoTerbuka", False), buka(12))),
        ("lightbox_info", lambda: (win.setWidth(1130), win.setHeight(696), lb.setProperty("infoTerbuka", True))),
        ("lightbox_wajah", lambda: (win.setWidth(1366), win.setHeight(720), wajah_contoh(), buka(12), lb.setProperty("kotakWajah", True), lb.setProperty("tab", "orang"))),
        ("mengenali", lambda: (lb.setProperty("infoTerbuka", False), lb.setProperty("indeks", -1), win.setProperty("menuAktif", 4), pura_pura_wajah())),
        ("orang", lambda: (selesai_pindai(), orang_contoh(), win.setProperty("menuAktif", 2))),
        ("orang_terang", lambda: pengaturan.aturTema("terang")),
        ("tinjau", lambda: (pengaturan.aturTema("gelap"), orang.mulaiTinjau(), hal.setProperty("halaman", "tinjau"))),
        ("kelola", lambda: (orang.bukaWajah(orang.daftar[0]["id"]), hal.setProperty("halaman", "wajah"))),
        ("filter", lambda: (win.setWidth(1130), win.setHeight(696), hal.setProperty("halaman", "daftar"), win.setProperty("menuAktif", 1), filter_terbuka(), galeri.aturPanel({"orang_panel": [orang.daftar[1]["id"]], "salah_satu": True, "orientasi": "lanskap"}))),
        ("filter_terang", lambda: pengaturan.aturTema("terang")),
        ("cari_saran", lambda: (pengaturan.aturTema("gelap"), galeri.aturPanel({}), filter_terbuka(False), win.setProperty("menuAktif", 0), QMetaObject.invokeMethod(win.findChild(QObject, "kotakCari"), "fokus", Qt.ConnectionType.DirectConnection), win.findChild(QObject, "kotakCari").setProperty("teksUji", "a"), cari.ketik("a"))),
        ("cari", lambda: (QMetaObject.invokeMethod(win.findChild(QObject, "kotakCari"), "tutup", Qt.ConnectionType.DirectConnection), win.setProperty("menuAktif", 3))),
        ("cari_hasil", lambda: cari.dariWajah(galeri._c.execute("SELECT min(id) FROM face").fetchone()[0])),
        ("foto_orang", lambda: (galeri.saringOrang(orang.daftar[1]["id"]), win.setProperty("menuAktif", 1))),
        ("sempit_720", lambda: win.setWidth(720)),
        ("orang_baru", lambda: (win.setWidth(1366), lb.setProperty("indeks", -1), galeri.hapusSaring(), pengaturan.aturTema("gelap"), hal.setProperty("halaman", "daftar"), win.setProperty("menuAktif", 2))),
        ("beri_nama", lambda: (orang.mulaiTinjau(), hal.setProperty("halaman", "tinjau"))),
        ("beri_nama_terang", lambda: pengaturan.aturTema("terang")),
        ("lokasi_terang", lambda: (hal.setProperty("halaman", "daftar"), win.setProperty("menuAktif", 4))),
        ("lokasi_hilang", lambda: (pengaturan.aturTema("gelap"), galeri._set_akar({1: None}))),
        ("lightbox_720", lambda: (buka(12))),
        ("lightbox_masuk", lambda: (win.setWidth(1366), lb.setProperty("kotakAsal", QRectF(300, 200, 200, 150)), lb.setProperty("masuk", 0.35))),
    ])

    if nama:
        QTimer.singleShot(1800, lambda: (win.grabWindow().save(str(KELUAR / f"{nama}.png")), app.quit()))
        return app.exec()

    def jalan(i=0):
        if i == len(langkah):
            app.quit()
            return
        n, f = langkah[i]
        f()
        QTimer.singleShot(1400, lambda: (win.grabWindow().save(str(KELUAR / f"{n}.png")), jalan(i + 1)))

    QTimer.singleShot(1500, jalan)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
