"""Perilaku yang ditambahkan desain baru: panel filter, aksen Windows, grup per bulan, rincian penampil."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from core import db, library, pipa_wajah  # noqa: E402

JAN = 1609459200  # 2021-01-01 UTC
JUL = 1625097600  # 2021-07-01 UTC
Y22 = 1656633600  # 2022-07-01 UTC


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def jalur(tmp_path):
    p = tmp_path / "library.db"
    c = db.buka(p)
    c.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'','x','C:','A'), (2,'','y','D:','B')")
    data = [(1, "f/a.jpg", 4000, 3000, JAN), (1, "b.jpg", 1000, 2000, JUL), (2, "c.jpg", 2000, 2000, Y22), (2, "g/d.jpg", 1280, 720, Y22 + 60)]
    for i, (s, rel, w, h, t) in enumerate(data, 1):
        c.execute("INSERT INTO photo(id, source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (?,?,?,1,1,?,?,?,?,'ok')",
                  (i, s, rel, f"{i:040x}", w, h, t))
    c.execute("INSERT INTO person(id, nama, dibuat) VALUES (1,'Ayu',1), (2,'Budi',1)")
    for foto, orang in ((1, 1), (2, 2), (3, 1), (3, 2)):
        c.execute("INSERT INTO face(photo_id,x1,y1,x2,y2,titik,skor,lebar_px,tajam,frontal,kualitas,embedding,model,person_id,state) "
                  "VALUES (?,0.1,0.1,0.5,0.5,x'00',1,1,1,1,1,x'00','m',?,'otomatis')", (foto, orang))
    c.commit()
    c.close()
    return p


def _id(c, s):
    return sorted(f.id for f in library.semua_foto(c, s))


@pytest.mark.parametrize("saring, harap", [
    ({"orientasi": "potret"}, [2]),
    ({"orientasi": "lanskap"}, [1, 4]),
    ({"orientasi": "persegi"}, [3]),
    ({"resolusi": 3840}, [1]),
    ({"resolusi": 1920}, [1, 2, 3]),
    ({"source": 2}, [3, 4]),
    ({"orang_panel": [1, 2]}, [3]),
    ({"orang_panel": [1, 2], "salah_satu": True}, [1, 2, 3]),
    ({"folder": {"source": 2, "rel": ""}}, [3, 4]),
    ({"folder": {"source": 2, "rel": ""}, "orientasi": "persegi"}, [3]),
])
def test_saringan_panel(jalur, saring, harap):
    assert _id(db.buka(jalur), saring) == harap


def test_tahun_terbaru_dulu(jalur):
    assert library.tahun_foto(db.buka(jalur)) == [2022, 2021]


def _galeri(jalur, **k):
    from ui.bridge.galeri import Galeri

    g = Galeri(jalur, jalur.parent / "th", **k)
    g.atur(900)
    return g


def test_panel_menyaring_dan_menghitung(jalur):
    g = _galeri(jalur)
    g.aturPanel({"orientasi": "lanskap", "resolusi": 0, "orang_panel": []})
    assert g.jumlah == 2 and g.panel == {"orientasi": "lanskap"} and g.jumlahPanel == 1
    g.aturPanel({"orang_panel": [1], "salah_satu": True})
    assert g.jumlahPanel == 1 and g.jumlah == 2


def test_panel_memuat_galeri_tertunda(jalur):
    g = _galeri(jalur, muat_awal=False)
    assert g.jumlah == 0
    g.aturPanel({"source": 1})
    assert g.jumlah == 2


def test_berpindah_tampilan_mengosongkan_panel(jalur):
    g = _galeri(jalur)
    g.aturPanel({"orientasi": "potret"})
    g.saring({"folder": {"source": 2, "rel": ""}, "label": "B"})
    assert g.panel == {} and g.jumlah == 2


def test_keluar_lewat_menu_mengosongkan_panel(jalur):
    g = _galeri(jalur)
    g.aturPanel({"orientasi": "potret"})
    g.hapusSaring()
    assert g.panel == {} and g.jumlah == 4


def test_navigasi_keyboard_antar_baris(jalur):
    g = _galeri(jalur)
    g.atur(260)  # cukup sempit agar foto terbagi ke beberapa baris
    g.lihat(0, 800)
    assert g.fotoDi(0) == 0
    bawah = g.tetangga(0, 1)
    assert bawah == g._tata.baris[g._baris_foto(bawah)].isi[0].indeks and g.yFoto(bawah) > g.yFoto(0)
    assert g.tetangga(bawah, -1) == 0
    assert g.tetangga(0, -1) == 0
    akhir = g.jumlah - 1
    assert g.tetangga(akhir, 1) == akhir


def test_panel_memperhalus_saringan_aktif(jalur):
    g = _galeri(jalur)
    g.saring({"folder": {"source": 2, "rel": ""}, "label": "B"})
    g.aturPanel({"orientasi": "persegi"})
    assert g.jumlah == 1 and g.labelSaring == "B"


def test_galeri_dinding_foto_tanpa_kepala_tanggal(jalur):
    g = _galeri(jalur)
    assert [b.label for b in g._tata.baris if b.jenis == "kepala"] == [""]
    assert g.tanggalDi(0) == "1 Juli 2022"


def test_koleksi_berisi_terbaru_kenangan_orang_folder(jalur):
    k = library.koleksi(db.buka(jalur), 2023, 7, 1)
    assert [x["judul"] for x in k][:2] == ["Terbaru", "Kenangan hari ini"]
    assert k[0]["saring"] == {"tahun": 2022, "bulan": 7, "label": "Juli 2022"}
    assert sorted(k[1]["saring"]["foto"]) == [2, 3, 4] and k[1]["jumlah"] == 3
    assert {x["judul"] for x in k[2:]} >= {"Ayu", "Budi"}
    assert any(x.get("saring", {}).get("folder") == {"source": 1, "rel": "f"} for x in k)
    assert len(k) <= 5 and all(x["sha1"] for x in k)


def test_koleksi_kosong_tanpa_kenangan_memakai_bulan_ini(jalur):
    k = library.koleksi(db.buka(jalur), 2023, 7, 15)
    assert k[1]["judul"] == "Kenangan bulan ini" and sorted(k[1]["saring"]["foto"]) == [2, 3, 4]


def test_koleksi_hanya_di_galeri_tanpa_saringan(jalur):
    g = _galeri(jalur)
    assert len(g.koleksi) >= 2 and g._tata.baris[0].tinggi == g.tinggiKoleksi
    g.aturPanel({"orientasi": "potret"})
    assert g._tata.baris[0].tinggi == 0
    g.aturPanel({})
    g.saring({"orang": [1], "label": "Ayu"})
    assert g._tata.baris[0].tinggi == 0


def test_jarak_foto_lapang_seperti_referensi(jalur):
    assert _galeri(jalur).jarak == 16


def test_rincian_foto_untuk_penampil(jalur):
    g = _galeri(jalur)
    i = g.indeksFoto(3)
    f = g.foto(i)
    assert f["lebar"] == 2000 and f["format"] == "JPG"
    assert len(f["wajah"]) == 2 and f["wajah"][0]["url"].startswith("image://wajah/")


def test_titik_bulan_tidak_berdempet(jalur):
    g = _galeri(jalur)
    assert len(g.titik(1000)) >= 1
    assert len(g.titik(5)) == 1


def test_halaman_awal_tersimpan(tmp_path):
    from ui.bridge.pengaturan import Pengaturan

    p = Pengaturan(tmp_path / "a.json")
    assert p.halamanAwal == "galeri"
    p.aturHalamanAwal("folder")
    assert Pengaturan(tmp_path / "a.json").halamanAwal == "folder"


HT = {"klien": 1, "judul": 2, "kiri": 10, "kanan": 11, "atas": 12, "kiri_atas": 13, "kanan_atas": 14, "bawah": 15, "kiri_bawah": 16, "kanan_bawah": 17, "maks": 9}


@pytest.mark.parametrize("x, y, kontrol, maks, harap", [
    (500, 30, "", False, "judul"),
    (500, 30, "kontrol", False, "klien"),
    (900, 30, "maks", False, "maks"),
    (500, 300, "", False, "klien"),
    (2, 300, "", False, "kiri"),
    (997, 300, "", False, "kanan"),
    (500, 2, "", False, "atas"),
    (500, 697, "", False, "bawah"),
    (2, 2, "", False, "kiri_atas"),
    (997, 2, "", False, "kanan_atas"),
    (2, 697, "", False, "kiri_bawah"),
    (997, 697, "", False, "kanan_bawah"),
    (2, 300, "", True, "klien"),
    (500, 2, "", True, "judul"),
])
def test_kode_hit_bingkai(x, y, kontrol, maks, harap):
    from ui.bridge.bingkai import kode_hit

    assert kode_hit(x, y, 1000, 700, 5, 48, kontrol, maks) == HT[harap]


@pytest.fixture
def jendela(jalur):
    from PySide6.QtCore import QObject, QtMsgType, qInstallMessageHandler
    from PySide6.QtTest import QTest

    import main

    galat = []
    lama = qInstallMessageHandler(lambda j, _k, m: galat.append(m) if j != QtMsgType.QtDebugMsg else None)
    mesin = main.buat_mesin_qml(jalur.parent, mulai_wajah=False)
    win = mesin.rootObjects()[0]
    QTest.qWait(50)
    yield mesin, win, QObject, QTest
    qInstallMessageHandler(lama)
    galat = [g for g in galat if "Cannot open" not in g]  # data uji tidak punya berkas thumbnail
    assert not [g for g in galat if "qml" in g.lower() or "binding" in g.lower() or "typeerror" in g.lower()], galat


def _panggil(obj, nama, *arg):
    from PySide6.QtCore import Q_ARG, QMetaObject, Qt

    QMetaObject.invokeMethod(obj, nama, Qt.ConnectionType.DirectConnection, *[Q_ARG("QVariant", a) for a in arg])


def test_buka_aplikasi_langsung_ke_galeri(jendela):
    mesin, win, _, QTest = jendela
    QTest.qWait(150)
    assert win.property("menuAktif") == 1 and mesin._jembatan[0].jumlah == 4


def test_halaman_awal_folder_tidak_memuat_galeri(jalur):
    import json

    from PySide6.QtTest import QTest

    import main

    (jalur.parent / "pengaturan.json").write_text(json.dumps({"halamanAwal": "folder"}), encoding="utf-8")
    mesin = main.buat_mesin_qml(jalur.parent, mulai_wajah=False)
    win = mesin.rootObjects()[0]
    QTest.qWait(150)
    assert win.property("menuAktif") == 0 and mesin._jembatan[0].jumlah == 0


def test_menu_galeri_memuat_foto(jendela):
    mesin, win, _, QTest = jendela
    _panggil(win, "pilihMenu", 1)
    QTest.qWait(30)
    assert win.property("menuAktif") == 1 and mesin._jembatan[0].jumlah == 4


def test_saran_cari_membawa_ke_foto_orang_dan_kembali(jendela):
    mesin, win, QObject, QTest = jendela
    galeri, _, _, _, cari, _ = mesin._jembatan
    kotak = win.findChild(QObject, "kotakCari")
    cari.ketik("ayu")
    _panggil(kotak, "jalankan", 0)
    QTest.qWait(30)
    assert win.property("menuAktif") == 1 and galeri.labelSaring == "Ayu" and galeri.jumlah == 2
    assert win.property("asalSaring") == 1  # dicari dari Galeri, Kembali ke Galeri


def test_lightbox_dibuka_dengan_gerak_dan_selesai(jendela):
    from PySide6.QtCore import QRectF

    mesin, win, QObject, QTest = jendela
    _panggil(win, "pilihMenu", 1)
    lb = win.findChild(QObject, "lightbox")
    _panggil(lb, "buka", 0, QRectF(100, 100, 200, 150))
    for _ in range(150):  # waktu animasi bergantung pada beban mesin
        if lb.property("masuk") == 1 and lb.property("terbuka"):
            break
        QTest.qWait(20)
    assert lb.property("terbuka") and lb.property("masuk") == 1
    assert lb.property("foto")["nama"] == "d.jpg"
    _panggil(lb, "keluar")
    for _ in range(150):  # waktu animasi bergantung pada beban mesin
        if lb.property("masuk") == 1 and not lb.property("terbuka"):
            break
        QTest.qWait(20)
    assert not lb.property("terbuka") and lb.property("masuk") == 1


def test_foto_dari_folder_kembali_ke_folder(jendela):
    mesin, win, QObject, QTest = jendela
    lb = win.findChild(QObject, "lightbox")
    _panggil(win, "bukaDariFolder", {"foto": [1, 2], "label": "Foto terbaru"}, 2)
    QTest.qWait(30)
    assert lb.property("terbuka") and win.property("menuAktif") == 1
    _panggil(lb, "tutup")
    QTest.qWait(30)
    assert win.property("menuAktif") == 0 and not mesin._jembatan[0].adaSaring


def test_sumber_bisa_diarahkan_ke_lokasi_baru(tmp_path):
    import shutil

    from PIL import Image
    from PySide6.QtCore import QUrl
    from PySide6.QtTest import QTest

    from core import scanner
    from ui.bridge.galeri import Galeri
    from ui.bridge.pindai import Pindai

    akar = tmp_path / "foto"
    (akar / "x").mkdir(parents=True)
    Image.new("RGB", (64, 48), (9, 9, 9)).save(akar / "x" / "a.jpg")
    c = db.buka(tmp_path / "library.db")
    sid = library.tambah_sumber(c, str(akar))
    scanner.Pemindai(c, tmp_path / "th", pekerja=1).jalankan(sid)
    c.close()
    shutil.move(akar, tmp_path / "pindah")
    (tmp_path / "asing").mkdir()
    Image.new("RGB", (64, 48)).save(tmp_path / "asing" / "z.jpg")

    g = Galeri(tmp_path / "library.db", tmp_path / "th")
    p = Pindai(tmp_path / "library.db", tmp_path / "th", g, pekerja=1)

    def tunggu():
        for _ in range(400):
            QTest.qWait(25)
            if not p.aktif and not p.mencariLokasi:
                return
        raise AssertionError("tidak selesai")

    p.pindahkan(sid, QUrl.fromLocalFile(str(tmp_path / "asing")).toString())
    tunggu()
    assert "tidak ada foto yang dikenali" in p.pesan and p.sumber[0]["jalur"].endswith("foto")
    p.pindahkan(sid, QUrl.fromLocalFile(str(tmp_path / "pindah")).toString())
    tunggu()
    assert p.sumber[0]["jalur"].endswith("pindah") and p.sumber[0]["ok"] == 1 and p.sumber[0]["hilang"] == 0


def _pindai_dengan_sumber(tmp_path):
    from ui.bridge.galeri import Galeri
    from ui.bridge.pindai import Pindai

    (tmp_path / "foto").mkdir()
    c = db.buka(tmp_path / "library.db")
    sid = library.tambah_sumber(c, str(tmp_path / "foto"))
    c.close()
    g = Galeri(tmp_path / "library.db", tmp_path / "th")
    return Pindai(tmp_path / "library.db", tmp_path / "th", g, pekerja=1), sid


def test_lokasi_baru_ditolak_bila_sumber_sudah_dihapus(tmp_path):
    p, sid = _pindai_dengan_sumber(tmp_path)
    (tmp_path / "baru").mkdir()
    p._mencari_lokasi = True
    library.hapus_sumber(p._c, sid)
    p._usai_cek_lokasi(sid, str(tmp_path / "baru"), (0, 0))
    assert not p.aktif and not p.mencariLokasi and "belum diganti" in p.pesan


def test_lokasi_baru_ditolak_bila_ada_pekerjaan_berjalan(tmp_path):
    p, sid = _pindai_dengan_sumber(tmp_path)
    (tmp_path / "baru").mkdir()
    p._mencari_lokasi = p._aktif = True
    p._usai_cek_lokasi(sid, str(tmp_path / "baru"), (0, 0))
    assert p.sumber[0]["jalur"].endswith("foto") and "belum diganti" in p.pesan


def test_kemajuan_wajah_untuk_halaman_lokasi(tmp_path):
    p, sid = _pindai_dengan_sumber(tmp_path)
    for i in range(3):
        p._c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status, wajah_model) "
                     "VALUES (?,?,1,1,?,4,3,1,'ok',?)", (sid, f"{i}.jpg", f"{i:040x}", pipa_wajah.MODEL if i == 0 else None))
    p._c.commit()
    p.sumberBerubah.emit()
    assert (p.wajahSelesai, p.wajahTotal) == (1, 3)


def test_tema_krem_lama_kembali_mengikuti_windows(tmp_path):
    import json

    from ui.bridge.pengaturan import Pengaturan

    (tmp_path / "a.json").write_text(json.dumps({"tema": "krem"}), encoding="utf-8")
    assert Pengaturan(tmp_path / "a.json").tema == "auto"


def test_sumber_tidak_bisa_dihapus_selama_lokasi_diperiksa(tmp_path):
    p, sid = _pindai_dengan_sumber(tmp_path)
    p._mencari_lokasi = True
    p.hapus(sid)
    p.pindai(sid)
    assert len(p.sumber) == 1 and not p.aktif


def test_panel_filter_tanpa_galat_dan_bisa_dihapus(jendela):
    mesin, win, QObject, QTest = jendela
    galeri = mesin._jembatan[0]
    _panggil(win, "pilihMenu", 1)
    win.findChild(QObject, "galeriHalaman").setProperty("filterTerbuka", True)
    QTest.qWait(30)
    panel = win.findChild(QObject, "panelFilter")
    _panggil(panel, "alih", "orientasi", "potret")
    assert galeri.jumlah == 1 and galeri.panel == {"orientasi": "potret"}
    _panggil(panel, "alih", "orientasi", "potret")
    assert galeri.jumlah == 4
    _panggil(panel, "alihOrang", 1)
    _panggil(panel, "alihOrang", 2)
    assert galeri.jumlah == 1
    _panggil(panel, "ubah", "salah_satu", True)
    assert galeri.jumlah == 3


def test_aksen_memakai_palet_windows():
    from ui.bridge.pengaturan import aksen_dari_palet

    palet = bytes.fromhex("99ebff00 4cc2ff00 0091f800 0078d400 0067c000 003e9200 001a6800 f7630c00")
    assert aksen_dari_palet(palet) == {"gelap": "#4cc2ff", "isi_gelap": "#0067c0", "pada_gelap": "#ffffff",
                                       "terang": "#0067c0", "isi_terang": "#0067c0", "pada_terang": "#ffffff"}


@pytest.mark.parametrize("palet, pada", [(b"", "#ffffff"), (b"\x00" * 32, "#ffffff"), (b"\xff" * 32, "#000000")])
def test_aksen_yang_tak_terbaca_tetap_terbaca(palet, pada):
    from ui.bridge.pengaturan import _kontras, aksen_dari_palet

    a = aksen_dari_palet(palet)
    assert _kontras(a["gelap"], "#0a0a0a") >= 3 and _kontras(a["terang"], "#f3f3f3") >= 3
    assert a["pada_gelap"] == pada and _kontras(a["pada_gelap"], a["isi_gelap"]) >= 4.5
