import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from core import db  # noqa: E402
from ui.bridge.galeri import SLOT, Galeri, label_hari  # noqa: E402

HARI = 86400
AWAL = 1_700_000_000


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QGuiApplication.instance() or QGuiApplication([])


def isi_db(p, n):
    c = db.buka(p)
    c.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'','x','C:','x')")
    c.executemany(
        "INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (1,?,1,1,?,?,?,?,'ok')",
        [(f"{i}.jpg", f"{i:040x}", 1500, 1000, AWAL - (i // 6) * HARI) for i in range(n)])
    c.commit()
    c.close()


@pytest.fixture
def galeri(tmp_path):
    isi_db(tmp_path / "a.db", 600)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    g.atur(1000)
    g.lihat(0, 800)
    return g


def rekam(g):
    hasil = []
    g.geserKe.connect(hasil.append)
    return hasil


def test_ubah_lebar_di_puncak_tidak_menggeser(galeri):
    r = rekam(galeri)
    galeri.atur(800)
    assert r == []


def test_ubah_lebar_menjaga_foto_teratas(galeri):
    t = galeri._tata
    i = next(k for k, b in enumerate(t.baris) if k > 20 and b.jenis == "foto" and t.baris[k - 1].jenis == "foto")
    galeri.lihat(t.baris[i].y, 800)
    id_foto = galeri._foto[t.baris[i].isi[0].indeks].id
    r = rekam(galeri)
    galeri.atur(700)
    baris_baru = next(b for b in galeri._tata.baris if any(galeri._foto[s.indeks].id == id_foto for s in b.isi))
    assert len(r) == 1 and r[0] <= baris_baru.y and baris_baru.y - r[0] <= 60


def test_slot_mengikuti_jendela(galeri):
    t = galeri._tata
    galeri.lihat(t.baris[60].y, 800)
    aktif = [i for i in galeri._slot if i >= 0]
    assert len(aktif) == len(set(aktif)) and len(aktif) <= SLOT
    for i in aktif:
        assert galeri._slot[i % SLOT] == i


def test_gulir_satu_baris_hanya_mengubah_sedikit_slot(galeri):
    t = galeri._tata
    galeri.lihat(t.baris[40].y, 800)
    ubah = []
    galeri.dataChanged.connect(lambda a, b: ubah.append(a.row()))
    galeri.lihat(t.baris[41].y, 800)
    assert 1 <= len(ubah) <= 3


def _baris_dekat(g, y, h):
    from ui.bridge.galeri import MARGIN

    return [i for i, b in enumerate(g._tata.baris) if b.y < y + h + MARGIN and b.y + b.tinggi > y - MARGIN]


def test_lompat_jauh_hanya_mengisi_baris_dekat_layar(galeri):
    # menyeret penggulir: tiap slot yang diganti membangun ulang deretan foto di QML, jadi isi yang terlihat saja
    y = galeri._tata.baris[len(galeri._tata.baris) - 20].y
    ubah = []
    galeri.dataChanged.connect(lambda a, b: ubah.append(a.row()))
    galeri.lihat(y, 800)
    dekat = _baris_dekat(galeri, y, 800)
    assert all(galeri._slot[i % SLOT] == i for i in dekat)
    assert len(ubah) <= len(dekat) < SLOT // 2


def test_slot_tersisa_selalu_cocok_dengan_tata_terkini(galeri):
    galeri.lihat(galeri._tata.baris[100].y, 800)
    galeri.atur(700)  # tata berubah: slot di luar layar yang masih memegang baris lama harus dikosongkan
    for s, i in enumerate(galeri._slot):
        if i >= 0:
            assert galeri._tanda[s] == galeri._tanda_baris(i)


def test_muat_ulang_tanpa_perubahan_tidak_membangun_ulang(galeri):
    ubah = []
    galeri.dataChanged.connect(lambda a, b: ubah.append(a.row()))
    galeri.muatUlang()
    assert ubah == []


def test_pustaka_menyusut_tidak_galat(tmp_path):
    isi_db(tmp_path / "a.db", 600)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    g.atur(1000)
    t = g._tata
    g.lihat(t.baris[len(t.baris) - 5].y, 800)
    with g._c:
        g._c.execute("DELETE FROM photo WHERE rowid > 30")
    g.muatUlang()
    for s in range(SLOT):
        g.data(g.index(s), g.ISI)


def test_pustaka_menyusut_saat_jendela_tanpa_tinggi_tidak_galat(tmp_path):
    isi_db(tmp_path / "a.db", 600)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    g.atur(1000)
    g.lihat(g._tata.baris[-5].y, 800)
    g.lihat(g._tata.baris[-5].y, 0)  # jendela diperkecil habis
    with g._c:
        g._c.execute("DELETE FROM photo WHERE rowid > 30")
    g.muatUlang()
    for s in range(SLOT):
        g.data(g.index(s), g.ISI)


def test_foto_mengembalikan_rincian(galeri):
    f = galeri.foto(0)
    assert f["pratinjau"].endswith(f"{5:040x}.1024.jpg")  # tanggal sama: id terbesar lebih dulu
    assert f["tanggal"] == label_hari(AWAL)
    assert galeri.foto(99999) == {}


def test_status_drive_sampai_ke_qml(galeri):
    galeri._terhubung.berubah.emit({1: None})
    assert galeri.tersambung == {"1": False}


def test_label_hari_indonesia():
    assert label_hari(1614834367) == "Kamis, 4 Maret 2021"


def test_pindai_dari_jembatan_mengisi_galeri(tmp_path):
    import time

    from PIL import Image
    from PySide6.QtCore import QUrl

    from ui.bridge.pindai import Pindai

    akar = tmp_path / "foto"
    akar.mkdir()
    Image.new("RGB", (300, 200), (1, 2, 3)).save(akar / "a.jpg", "JPEG")
    Image.new("RGB", (300, 200), (9, 2, 3)).save(akar / "b.jpg", "JPEG")
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    p = Pindai(tmp_path / "a.db", tmp_path / "th", g, pekerja=1)
    p._harus_jeda = lambda: False  # laptop uji bisa saja memakai baterai
    p.tambah(QUrl.fromLocalFile(str(akar)).toString())
    assert p.aktif
    app = QGuiApplication.instance()
    batas = time.monotonic() + 40
    while p.aktif and time.monotonic() < batas:
        app.processEvents()
        time.sleep(0.02)
    assert not p.aktif and g.jumlah == 2
    assert p.pesan.startswith("Selesai: 2 foto baru")
    assert p.sumber[0]["ok"] == 2


def test_tanggal_ekstrem_tidak_menjatuhkan_aplikasi():
    assert label_hari(99_999_999_999_999)
    assert label_hari(-5)


def test_indeks_foto_mengikuti_muat_ulang(tmp_path):
    isi_db(tmp_path / "a.db", 20)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    g.atur(1000)
    id_foto = g.foto(10)["id"]
    with g._c:
        g._c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) "
                     "VALUES (1,'baru.jpg',1,1,'ff',10,10,?,'ok')", (AWAL + HARI,))
    g.muatUlang()
    assert g.indeksFoto(id_foto) == 11
    assert g.indeksFoto(-1) == -1


def test_tampilkan_di_folder_indeks_salah_tidak_galat(galeri):
    galeri.tampilkanDiFolder(99999)


def test_jeda_melepas_penjaga_terjaga(tmp_path, monkeypatch):
    from core import daya
    from ui.bridge import pindai as modul

    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    p = modul.Pindai(tmp_path / "a.db", tmp_path / "th", g, pekerja=1)
    catat = []
    monkeypatch.setattr(daya, "pakai_baterai", lambda: True)
    monkeypatch.setattr(daya, "jaga_terjaga", catat.append)
    assert p._harus_jeda() is True
    assert catat == [False]
    monkeypatch.setattr(daya, "pakai_baterai", lambda: False)
    assert p._harus_jeda() is False
    assert catat == [False, True]


def _tunggu(p, batas=40):
    import time

    app = QGuiApplication.instance()
    akhir = time.monotonic() + batas
    while p.aktif and time.monotonic() < akhir:
        app.processEvents()
        time.sleep(0.02)
    assert not p.aktif


def _pindai_tahap_wajah(tmp_path, monkeypatch, kerja_palsu):
    from ui.bridge import pindai as modul

    isi_db(tmp_path / "a.db", 3)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    p = modul.Pindai(tmp_path / "a.db", tmp_path / "th", g, pekerja=1, model=("d", "r", 1))
    monkeypatch.setattr(modul.pipa_wajah, "PemindaiWajah", kerja_palsu)
    return p


def test_tahap_wajah_berjalan_dan_melapor(tmp_path, monkeypatch):
    from core.pipa_wajah import RingkasanWajah

    class Palsu:
        def __init__(self, c, thumb, model):
            pass

        def jalankan(self, batal, jeda, lapor):
            lapor(1, 3)
            return RingkasanWajah(total=3, selesai=3, wajah=5)

    p = _pindai_tahap_wajah(tmp_path, monkeypatch, Palsu)
    p.lanjutkanWajah()
    assert p.aktif and p.tahap == "wajah"
    _tunggu(p)
    assert p.tahap == "" and p.pesan == "Selesai: 5 wajah ditemukan di 3 foto."


def test_pindai_foto_mendahului_wajah_yang_berjalan(tmp_path, monkeypatch):
    from core.pipa_wajah import RingkasanWajah

    class Palsu:
        def __init__(self, c, thumb, model):
            pass

        def jalankan(self, batal, jeda, lapor):
            assert batal.wait(20)
            return RingkasanWajah(total=3, dibatalkan=True)

    p = _pindai_tahap_wajah(tmp_path, monkeypatch, Palsu)
    urutan = []
    p._mulai_berikut = lambda: urutan.append("foto")
    p.lanjutkanWajah()
    p.pindai(1)
    assert p._batal.is_set()
    _tunggu(p)
    assert urutan == ["foto"]


def test_tanpa_pekerjaan_wajah_tidak_mulai(tmp_path, monkeypatch):
    p = _pindai_tahap_wajah(tmp_path, monkeypatch, None)
    with p._c:
        p._c.execute("UPDATE photo SET wajah_model=?", (modul_model(),))
    p.lanjutkanWajah()
    assert not p.aktif


def modul_model():
    from core.pipa_wajah import MODEL

    return MODEL


def test_foto_membawa_kotak_wajah(tmp_path):
    isi_db(tmp_path / "a.db", 1)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    with g._c:
        g._c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, "
                     "embedding, model) VALUES (1,0.1,0.2,0.3,0.4,x'00',1,1,1,1,1,x'00','m')")
    w = g.foto(0)["wajah"]
    assert [{k: v for k, v in x.items() if k != "url"} for x in w] == [{"id": 1, "x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4, "orang": -1, "nama": ""}]


def test_hapus_sumber_ditolak_saat_bekerja(tmp_path):
    from ui.bridge.pindai import Pindai

    isi_db(tmp_path / "a.db", 1)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    p = Pindai(tmp_path / "a.db", tmp_path / "th", g, pekerja=1)
    p._aktif = True
    p.hapus(1)
    assert len(p.sumber) == 1


def test_pesan_pindai_tidak_terhapus_saat_wajah_mulai(tmp_path, monkeypatch):
    from core.pipa_wajah import RingkasanWajah
    from core.scanner import Ringkasan

    class Palsu:
        def __init__(self, c, thumb, model):
            pass

        def jalankan(self, batal, jeda, lapor):
            return RingkasanWajah(total=3, selesai=3, wajah=5)

    p = _pindai_tahap_wajah(tmp_path, monkeypatch, Palsu)
    p._usai(Ringkasan(baru=3, gagal=2))
    assert p.tahap == "wajah"
    assert "2 tidak bisa dibuka" in p.pesan
    _tunggu(p)
    assert "2 tidak bisa dibuka" in p.pesan and "5 wajah" in p.pesan


def _isi_orang(tmp_path):
    from core import orang as o

    isi_db(tmp_path / "a.db", 12)
    c = db.buka(tmp_path / "a.db")
    pa = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    pb = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    v = b"\x00" * 1024
    for i, (ph, p) in enumerate([(1, pa), (2, pa), (3, pa), (4, pa), (5, pb), (6, pb), (7, pb)]):
        c.execute("INSERT INTO face(photo_id,x1,y1,x2,y2,titik,skor,lebar_px,tajam,frontal,kualitas,embedding,model,person_id,state) "
                  "VALUES (?,0.1,0.1,0.3,0.3,x'00',1,120,300,1,?,?,'m',?,'otomatis')", (ph, 0.9 - i * 0.01, v, p))
    c.commit()
    c.close()
    return pa, pb, o


def test_galeri_menyaring_foto_satu_orang(tmp_path):
    pa, _, _ = _isi_orang(tmp_path)
    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    r = rekam(g)
    g.saringOrang(pa)
    assert g.jumlah == 4 and r[-1] == 0 and g.orangAktif == pa
    g.saringOrang(-1)
    assert g.jumlah == 12


def test_tinjau_memberi_nama_dan_maju(tmp_path):
    from ui.bridge.orang import Orang

    pa, pb, _ = _isi_orang(tmp_path)
    o = Orang(tmp_path / "a.db")
    assert o.jumlahTinjau == 2
    o.mulaiTinjau()
    assert o.tinjau["id"] == pa and o.tinjau["urutan"] == 1 and len(o.tinjau["wajah"]) == 4
    o.simpanNama("  Ayu  ")
    assert o.tinjau["id"] == pb
    o.selesaiTinjau()
    assert o.jumlahTinjau == 1
    assert o.daftar[0]["nama"] == "Ayu" and o.namaSerupa("ay") == ["Ayu"]
    o.simpanNama("   ")  # nama kosong tidak memajukan antrean
    assert o.tinjau["id"] == pb
    o.lewati()
    assert o.tinjau["selesai"] is True
    o.lewati()
    assert o.tinjau["selesai"] is True


def test_tinjau_melewati_kelompok_yang_sudah_tergabung(tmp_path):
    from ui.bridge.orang import Orang

    pa, pb, mod = _isi_orang(tmp_path)
    o = Orang(tmp_path / "a.db")
    o.mulaiTinjau()
    mod.gabung(o._c, pb, pa)
    o.simpanNama("Ayu")
    assert o.tinjau["selesai"] is True


def test_kelola_bukan_dia_semua_menutup_halaman(tmp_path):
    from ui.bridge.orang import Orang

    pa, _, _ = _isi_orang(tmp_path)
    o = Orang(tmp_path / "a.db")
    o.bukaWajah(pa)
    ids = [w["id"] for w in o.wajahOrang["wajah"]]
    assert len(ids) == 4
    o.bukanDia(ids[:1])
    assert o.wajahOrang["jumlah"] == 3
    o.bukanDia(ids[1:])
    assert o.wajahOrang == {}


def test_potongan_wajah_bulat_beralfa(tmp_path):
    from PIL import Image

    from core import thumbs

    sha = "ab" * 20
    p = thumbs.jalur(tmp_path, sha, thumbs.BESAR)
    p.parent.mkdir(parents=True)
    Image.new("RGB", (1024, 683), (200, 100, 50)).save(p, "JPEG")
    for kotak in ([0.1, 0.1, 0.3, 0.3], [0.9, 0.9, 1.0, 1.0], [0.0, 0.0, 0.01, 0.01]):
        im = thumbs.potong_bulat(tmp_path, sha, kotak)
        assert im.size == (192, 192) and im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0 and im.getpixel((96, 96))[3] == 255


def test_penyedia_wajah_tidak_galat_saat_pratinjau_hilang(tmp_path):
    from PySide6.QtCore import QSize

    from ui.bridge.orang import PenyediaWajah

    im = PenyediaWajah(tmp_path).requestImage("ab/0.1,0.1,0.2,0.2", QSize(), QSize())
    assert im.width() == 1


def test_memajukan_tinjau_tidak_menyegarkan_daftar(tmp_path):
    from ui.bridge.orang import Orang

    _isi_orang(tmp_path)
    o = Orang(tmp_path / "a.db")
    o.mulaiTinjau()
    catat = []
    o.daftarBerubah.connect(lambda: catat.append(1))
    o.lewati()
    assert catat == []


def test_daftar_tidak_berubah_tidak_memberi_sinyal(tmp_path):
    from ui.bridge.orang import Orang

    _isi_orang(tmp_path)
    o = Orang(tmp_path / "a.db")
    catat = []
    o.daftarBerubah.connect(lambda: catat.append(1))
    o.segarkan()
    assert catat == []


def test_klik_kotak_wajah_membuka_orang(tmp_path):
    from PySide6.QtCore import QObject, QPoint, Qt
    from PySide6.QtQuick import QQuickWindow  # noqa: F401
    from PySide6.QtTest import QTest

    import main

    pa, _, _ = _isi_orang(tmp_path)
    c = db.buka(tmp_path / "a.db")
    c.execute("UPDATE face SET x1=0.3, y1=0.3, x2=0.7, y2=0.7")
    c.commit()
    c.execute("VACUUM INTO ?", (str(tmp_path / "library.db"),))
    c.close()
    mesin = main.buat_mesin_qml(tmp_path, mulai_wajah=False, muat_awal=True)
    app = QGuiApplication.instance()
    win = mesin.rootObjects()[0]
    galeri = mesin._jembatan[0]
    lb = win.findChild(QObject, "lightbox")
    i = next(k for k in range(galeri.jumlah) if galeri.foto(k)["wajah"] and galeri.foto(k)["wajah"][0]["orang"] == pa)
    win.show()
    lb.setProperty("indeks", i)
    lb.setProperty("foto", galeri.foto(i))
    lb.setProperty("kotakWajah", True)
    for _ in range(30):
        app.processEvents()
        QTest.qWait(10)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(win.width() // 2, (win.height() - 72) // 2))
    for _ in range(10):
        app.processEvents()
        QTest.qWait(10)
    assert galeri.orangAktif == pa and lb.property("indeks") == -1
    win.close()
