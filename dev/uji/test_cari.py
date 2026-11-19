import calendar
import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from core import cari, db, library  # noqa: E402
from core.pipa_wajah import MODEL  # noqa: E402

ACAK = np.random.default_rng(9)


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QGuiApplication.instance() or QGuiApplication([])


def unit():
    v = ACAK.standard_normal(512)
    return v / np.linalg.norm(v)


def dekat(c, s=0.03):
    v = c + ACAK.normal(0, s, 512)
    return v / np.linalg.norm(v)


@pytest.fixture
def c(tmp_path):
    k = db.buka(tmp_path / "library.db")
    k.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'','x','C:','x')")
    k.commit()
    return k


_n = [0]


def foto(c, rel=None, tgl=(2021, 3, 4), status="ok"):
    _n[0] += 1
    return c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (1,?,1,1,?,100,100,?,?)",
                     (rel or f"a/{_n[0]}.jpg", f"{_n[0]:040x}", calendar.timegm((*tgl, 10, 0, 0)), status)).lastrowid


def orang_baru(c, nama=None, sembunyi=0):
    return c.execute("INSERT INTO person(nama, tersembunyi, dibuat) VALUES (?,?,1)", (nama, sembunyi)).lastrowid


def wajah(c, v, photo, pid=None):
    return c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model, person_id) "
                     "VALUES (?,0.1,0.1,0.3,0.3,x'00',0.9,120,300,0.9,0.8,?,?,?)",
                     (photo, v.astype(np.float16).tobytes(), MODEL, pid)).lastrowid


# --- saringan
def test_saring_dua_orang_berarti_dan(c):
    a, b = orang_baru(c, "A"), orang_baru(c, "B")
    f1, f2, f3 = foto(c), foto(c), foto(c)
    wajah(c, unit(), f1, a)
    wajah(c, unit(), f1, b)
    wajah(c, unit(), f2, a)
    wajah(c, unit(), f3, b)
    c.commit()
    assert [f.id for f in library.semua_foto(c, {"orang": [a, b]})] == [f1]
    assert library.hitung(c, {"orang": [a, b]}) == 1
    assert library.hitung(c, {"orang": [a]}) == 2


def test_saring_folder_persis_bukan_awalan(c):
    f1 = foto(c, "Liburan/a.jpg")
    f2 = foto(c, "Liburan/sub/b.jpg")
    foto(c, "Liburan 2/c.jpg")
    c.commit()
    hasil = {f.id for f in library.semua_foto(c, {"folder": {"source": 1, "rel": "Liburan"}})}
    assert hasil == {f1, f2}


def test_saring_tahun_dan_bulan(c):
    f1 = foto(c, tgl=(2021, 3, 4))
    f2 = foto(c, tgl=(2021, 12, 31))
    foto(c, tgl=(2022, 1, 1))
    c.commit()
    assert {f.id for f in library.semua_foto(c, {"tahun": 2021})} == {f1, f2}
    assert {f.id for f in library.semua_foto(c, {"tahun": 2021, "bulan": 12})} == {f2}


def test_saring_id_foto_dan_status(c):
    f1, f2 = foto(c), foto(c, status="hilang")
    c.commit()
    assert [f.id for f in library.semua_foto(c, {"foto": [f1, f2]})] == [f1]


# --- saran teks
def test_saran_nama_orang_bernama(c):
    a = orang_baru(c, "Budi")
    orang_baru(c, "Sari")
    wajah(c, unit(), foto(c), a)
    c.commit()
    s = cari.saran_teks(c, "bud")
    assert [x["nama"] for x in s["orang"]] == ["Budi"] and s["orang"][0]["jumlah"] == 1


def test_saran_tidak_menampilkan_tersembunyi(c):
    a = orang_baru(c, "Budi", sembunyi=1)
    wajah(c, unit(), foto(c), a)
    c.commit()
    assert cari.saran_teks(c, "bud")["orang"] == []


def test_saran_folder_menurut_jumlah(c):
    for _ in range(3):
        foto(c, f"Wisuda/{_n[0]}.jpg")
    foto(c, f"Lama/wisuda kecil/{_n[0]}.jpg")
    c.commit()
    f = cari.saran_teks(c, "wisuda")["folder"]
    assert [(x["rel"], x["jumlah"]) for x in f] == [("Wisuda", 3), ("Lama/wisuda kecil", 1)]


def test_saran_tahun_dan_bulan_indonesia(c):
    foto(c, tgl=(2021, 3, 4))
    c.commit()
    assert cari.saran_teks(c, "2021")["tanggal"] == [{"label": "2021", "tahun": 2021, "bulan": 0, "jumlah": 1}]
    assert cari.saran_teks(c, "maret 2021")["tanggal"] == [{"label": "Maret 2021", "tahun": 2021, "bulan": 3, "jumlah": 1}]
    assert cari.saran_teks(c, "2030")["tanggal"] == []


def test_saran_kosong_untuk_teks_kosong(c):
    assert cari.saran_teks(c, "  ") == {"orang": [], "folder": [], "tanggal": []}


# --- indeks
def isi_indeks(c, n=6):
    p = unit()
    a = orang_baru(c, "Budi")
    ids = [wajah(c, dekat(p), foto(c), a) for _ in range(n)]
    lain = unit()
    b = orang_baru(c, "Sari")
    ids2 = [wajah(c, dekat(lain), foto(c), b) for _ in range(n)]
    c.commit()
    return p, lain, a, b, ids, ids2


def test_cari_menempatkan_orang_benar_di_atas(c):
    p, _, a, b, ids, _ = isi_indeks(c)
    h = cari.Indeks(c).cari(dekat(p))
    assert h["orang"][0]["id"] == a
    assert b not in [o["id"] for o in h["orang"]]
    assert {w["id"] for w in h["wajah"]} == set(ids)
    assert h["orang"][0]["pita"] in ("Sangat mirip", "Mirip", "Agak mirip")


def test_cari_mengecualikan_wajah_sumber(c):
    p, _, _, _, ids, _ = isi_indeks(c)
    i = cari.Indeks(c)
    h = i.cari(i.vektor(ids[0]), kecuali=ids[0])
    assert ids[0] not in {w["id"] for w in h["wajah"]}


def test_cari_mengabaikan_foto_hilang_dan_orang_tersembunyi(c):
    p, _, a, _, ids, _ = isi_indeks(c)
    c.execute("UPDATE photo SET status='hilang' WHERE id=(SELECT photo_id FROM face WHERE id=?)", (ids[0],))
    c.execute("UPDATE person SET tersembunyi=1 WHERE id=?", (a,))
    c.commit()
    h = cari.Indeks(c).cari(dekat(p))
    assert ids[0] not in {w["id"] for w in h["wajah"]}
    assert h["orang"] == []


def test_indeks_menyegarkan_saat_wajah_bertambah(c):
    p, _, a, _, ids, _ = isi_indeks(c)
    i = cari.Indeks(c)
    i.cari(dekat(p))
    baru = wajah(c, dekat(p), foto(c), a)
    c.commit()
    assert baru in {w["id"] for w in i.cari(dekat(p))["wajah"]}


def test_indeks_kosong(c):
    h = cari.Indeks(c).cari(unit())
    assert h == {"orang": [], "wajah": []}


def test_satu_wajah_keliru_tidak_mengangkat_orang(c):
    p = unit()
    a = orang_baru(c, "Benar")
    for _ in range(6):
        wajah(c, dekat(p), foto(c), a)
    b = orang_baru(c, "Keliru")
    wajah(c, dekat(p), foto(c), b)
    for _ in range(6):
        wajah(c, dekat(unit()), foto(c), b)
    c.commit()
    assert cari.Indeks(c).cari(dekat(p))["orang"][0]["id"] == a


def test_cepat_pada_45_ribu_wajah(c):
    i = cari.Indeks(c)
    i._muat_matriks(np.arange(45000), ACAK.standard_normal((45000, 512), np.float32) / 22.6)
    t = time.perf_counter()
    i._peringkat(unit().astype(np.float32), None)
    assert time.perf_counter() - t < 0.1


# --- jembatan
def _cari(tmp_path, c):
    import pembantu_cari
    from ui.bridge.cari import Cari

    c.close()
    return Cari(tmp_path / "library.db", tmp_path / "th", model=(), olah=pembantu_cari.contoh_palsu, muat=pembantu_cari.muat_palsu)


def _tunggu(b, batas=30):
    app = QGuiApplication.instance()
    akhir = time.monotonic() + batas
    while b.hasil.get("status") == "memproses" and time.monotonic() < akhir:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()


def test_contoh_satu_wajah_langsung_mencari(c, tmp_path):
    a = orang_baru(c, "Budi")
    v = np.zeros(512)
    v[0] = 1
    wajah(c, v, foto(c), a)
    c.commit()
    b = _cari(tmp_path, c)
    b.contoh(str(tmp_path / "x.jpg"))
    assert b.hasil["status"] == "memproses"
    _tunggu(b)
    assert b.hasil["status"] == "hasil" and b.hasil["orang"][0]["nama"] == "Budi"


def test_contoh_banyak_wajah_meminta_pilihan(c, tmp_path):
    a = orang_baru(c, "Budi")
    v = np.zeros(512)
    v[1] = 1
    wajah(c, v, foto(c), a)
    c.commit()
    b = _cari(tmp_path, c)
    b.contoh(str(tmp_path / "dua.jpg"))
    _tunggu(b)
    assert b.hasil["status"] == "pilih" and len(b.hasil["pilihan"]) == 2
    b.pilihWajah(1)
    _tunggu(b)
    assert b.hasil["status"] == "hasil" and b.hasil["orang"][0]["nama"] == "Budi"


def test_contoh_tanpa_wajah_dan_rusak_memberi_pesan(c, tmp_path):
    b = _cari(tmp_path, c)
    b.contoh(str(tmp_path / "kosong.jpg"))
    _tunggu(b)
    assert b.hasil["status"] == "pesan" and "wajah" in b.hasil["pesan"].lower()
    b.contoh(str(tmp_path / "rusak.jpg"))
    _tunggu(b)
    assert b.hasil["status"] == "pesan" and "tidak bisa" in b.hasil["pesan"].lower()


def test_contoh_url_berkas_diterima(c, tmp_path):
    from PySide6.QtCore import QUrl

    b = _cari(tmp_path, c)
    b.contohUrl(QUrl.fromLocalFile(str(tmp_path / "kosong.jpg")).toString())
    _tunggu(b)
    assert b.hasil["status"] == "pesan"


def test_format_tak_didukung_ditolak(c, tmp_path):
    b = _cari(tmp_path, c)
    b.contoh(str(tmp_path / "video.mp4"))
    assert b.hasil["status"] == "pesan" and "tidak bisa dipakai" in b.hasil["pesan"]


def test_dari_wajah_mencari_tanpa_diri_sendiri(c, tmp_path):
    p = unit()
    a = orang_baru(c, "Budi")
    ids = [wajah(c, dekat(p), foto(c), a) for _ in range(5)]
    c.commit()
    b = _cari(tmp_path, c)
    b.dariWajah(ids[0])
    _tunggu(b)
    assert b.hasil["status"] == "hasil"
    assert ids[0] not in [w["id"] for w in b.hasil["wajah"]] and len(b.hasil["wajah"]) == 4


def test_kata_kunci_dan_pilihan_saringan(c, tmp_path):
    a = orang_baru(c, "Budi")
    b_ = orang_baru(c, "Sari")
    f = foto(c, tgl=(2021, 3, 4))
    wajah(c, unit(), f, a)
    wajah(c, unit(), f, b_)
    wajah(c, unit(), foto(c), a)
    c.commit()
    b = _cari(tmp_path, c)
    b.ketik("bud")
    assert b.saran["orang"][0]["nama"] == "Budi"
    b.bersihkan()
    assert b.saran["orang"] == []


def test_saringan_galeri_dari_pilihan(tmp_path, c):
    from ui.bridge.galeri import Galeri

    a = orang_baru(c, "Budi")
    f1, _ = foto(c), foto(c)
    wajah(c, unit(), f1, a)
    c.commit()
    g = Galeri(tmp_path / "library.db", tmp_path / "th")
    g.saring({"orang": [a], "label": "Budi"})
    assert g.jumlah == 1 and g.labelSaring == "Budi" and g.adaSaring and g.orangAktif == a
    g.hapusSaring()
    assert g.jumlah == 2 and not g.adaSaring and g.orangAktif == -1


def test_saringan_dua_orang_tanpa_kelola(tmp_path, c):
    from ui.bridge.galeri import Galeri

    a, b_ = orang_baru(c, "Budi"), orang_baru(c, "Sari")
    f = foto(c)
    wajah(c, unit(), f, a)
    wajah(c, unit(), f, b_)
    c.commit()
    g = Galeri(tmp_path / "library.db", tmp_path / "th")
    g.saring({"orang": [a, b_], "label": "Budi + Sari"})
    assert g.orangAktif == -1 and g.labelSaring == "Budi + Sari" and g.jumlah == 1


def test_contoh_nyata_tanpa_wajah(tmp_path):
    from PIL import Image

    from core import pipa_wajah, thumbs

    m = Path(__file__).resolve().parents[2] / "models" / "buffalo_l"
    if not (m / "w600k_r50.onnx").exists():
        pytest.skip("model belum diunduh")
    p = tmp_path / "x.jpg"
    Image.new("RGB", (1600, 1200), (120, 130, 140)).save(p, "JPEG")
    pipa_wajah.muat(str(m / "det_10g.onnx"), str(m / "w600k_r50.onnx"), 2, None, "ort")  # kartu grafis tanpa cache = 90 dtk kompilasi
    sha, wajah_ = cari.olah_contoh(str(p), str(tmp_path / "th"))
    assert wajah_ == [] and thumbs.jalur(tmp_path / "th", sha, thumbs.BESAR).exists()


def test_wajah_yang_belum_terindeks_memberi_pesan_jelas(c, tmp_path):
    p = unit()
    f = c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model) "
                  "VALUES (?,0.1,0.1,0.3,0.3,x'00',0.9,120,300,0.9,0.8,?,'model-lama')", (foto(c), p.astype(np.float16).tobytes())).lastrowid
    c.commit()
    b = _cari(tmp_path, c)
    b.dariWajah(f)
    _tunggu(b)
    assert b.hasil["status"] == "pesan" and b.hasil["pesan"] == "Wajah ini belum selesai dikenali. Coba lagi nanti."


def test_saran_teks_memakai_hitungan_folder_tersimpan(c, tmp_path):
    foto(c, "Wisuda/a.jpg")
    c.commit()
    h = cari.hitung_folder(c)
    foto(c, "Wisuda/b.jpg")
    c.commit()
    assert cari.saran_teks(c, "wisuda", h)["folder"][0]["jumlah"] == 1
    assert cari.saran_teks(c, "wisuda")["folder"][0]["jumlah"] == 2


def test_jembatan_menyegarkan_hitungan_folder_saat_foto_bertambah(c, tmp_path):
    from core import db as dbm

    foto(c, "Wisuda/a.jpg")
    c.commit()
    b = _cari(tmp_path, c)
    b.ketik("wisuda")
    assert b.saran["folder"][0]["jumlah"] == 1
    k = dbm.buka(tmp_path / "library.db")
    foto(k, "Wisuda/b.jpg")
    k.commit()
    k.close()
    b.ketik("wisuda")
    assert b.saran["folder"][0]["jumlah"] == 2


def test_jawaban_contoh_lama_tidak_menimpa_vektor(c, tmp_path):
    b = _cari(tmp_path, c)
    b._token = 5
    b._vektor = ["baru", "baru"]
    b._terima(4, {"status": "hasil", "vektor": ["lama"]})
    assert b._vektor == ["baru", "baru"]
    b._terima(5, {"status": "pilih", "pilihan": [{"i": 0, "url": "u"}], "vektor": ["kini"]})
    assert b._vektor == ["kini"] and "vektor" not in b.hasil
    b.pilihWajah(9)  # indeks di luar batas diabaikan
    assert b.hasil["status"] == "pilih"


def test_indeks_segar_saat_id_wajah_dipakai_ulang(c):
    p, q = unit(), unit()
    f = foto(c)
    wajah(c, dekat(p), f)
    c.commit()
    i = cari.Indeks(c)
    i.cari(p)
    c.execute("DELETE FROM face")
    fid = wajah(c, dekat(q), f)
    c.execute("UPDATE face SET kualitas=0.3 WHERE id=?", (fid,))
    c.commit()
    assert [w["id"] for w in i.cari(q)["wajah"]] == [fid]


def test_saring_orang_mengganti_saringan_gabungan(tmp_path, c):
    from ui.bridge.galeri import Galeri

    a = orang_baru(c, "Budi")
    wajah(c, unit(), foto(c, tgl=(2021, 1, 1)), a)
    wajah(c, unit(), foto(c, tgl=(2022, 1, 1)), a)
    c.commit()
    g = Galeri(tmp_path / "library.db", tmp_path / "th")
    g.saring({"orang": [a], "tahun": 2021, "label": "Budi + 2021"})
    assert g.jumlah == 1
    g.saringOrang(a)
    assert g.jumlah == 2 and g.labelSaring == "Budi"
