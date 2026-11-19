import os
import sys
import threading
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core import db, faces, library, pipa_wajah, scanner, thumbs
from core.faces import TEMPLAT_112, Wajah


# --- kualitas
def wajah_acak(ukuran=112):
    arr = np.random.default_rng(1).integers(0, 255, (ukuran, ukuran, 3), np.uint8)
    return Image.fromarray(arr)


TITIK_LURUS = TEMPLAT_112.copy()


def test_tajam_lebih_tinggi_daripada_buram():
    tajam = wajah_acak()
    buram = tajam.filter(ImageFilter.GaussianBlur(4))
    a = pipa_wajah.nilai_kualitas(tajam, 0.9, 120, TITIK_LURUS)
    b = pipa_wajah.nilai_kualitas(buram, 0.9, 120, TITIK_LURUS)
    assert a["tajam"] > b["tajam"] and a["kualitas"] > b["kualitas"]


def test_wajah_kecil_berkualitas_lebih_rendah():
    g = wajah_acak()
    assert pipa_wajah.nilai_kualitas(g, 0.9, 30, TITIK_LURUS)["kualitas"] < pipa_wajah.nilai_kualitas(g, 0.9, 120, TITIK_LURUS)["kualitas"]


def test_wajah_miring_frontal_rendah():
    miring = TITIK_LURUS.copy()
    miring[2, 0] = miring[1, 0] - 1  # hidung hampir segaris mata kanan
    g = wajah_acak()
    a = pipa_wajah.nilai_kualitas(g, 0.9, 120, TITIK_LURUS)["frontal"]
    b = pipa_wajah.nilai_kualitas(g, 0.9, 120, miring)["frontal"]
    assert a > 0.9 and b < 0.5


# --- proses_foto: detektor dan pengenal palsu
class DetPalsu:
    """`halus(potongan)` meniru deteksi ulang pada potongan di sekitar satu wajah."""

    def __init__(self, wajah, halus=None):
        self.wajah, self.halus, self.panggilan = wajah, halus, []

    def deteksi(self, gambar, sisi=640, ambang=0.5):
        self.panggilan.append((gambar.size, sisi))
        if sisi == pipa_wajah.SISI_DETEKSI:
            return self.wajah
        return self.halus(gambar) if self.halus else []


class RecPalsu:
    def __init__(self):
        self.terima = []

    def embed(self, potongan):
        self.terima += potongan
        v = np.zeros((len(potongan), 512), np.float32)
        v[:, 0] = 1
        return v


def wajah_di(x, y, lebar):
    k = lebar / 112
    return Wajah(np.array([x, y, x + lebar, y + lebar], np.float32),
                 TEMPLAT_112 * k + [x, y], 0.9)


def test_tanpa_wajah_tidak_membaca_asli():
    def jangan():
        raise AssertionError("asli dibaca")

    assert pipa_wajah.proses_foto(Image.new("RGB", (1024, 683)), jangan, DetPalsu([]), RecPalsu()) == []


def test_wajah_besar_memakai_pratinjau():
    def jangan(sisi):
        raise AssertionError("asli dibaca")

    h = pipa_wajah.proses_foto(Image.new("RGB", (1024, 683)), jangan, DetPalsu([wajah_di(100, 100, 200)]), RecPalsu())
    assert len(h) == 1
    assert h[0][6] == pytest.approx(200)  # lebar_px
    assert h[0][0] == pytest.approx(100 / 1024)


def test_wajah_kecil_dipotong_dari_asli_dengan_koordinat_benar():
    pratinjau = Image.new("RGB", (1024, 512))
    asli = Image.new("RGB", (4096, 2048))
    w = wajah_di(100, 100, 56)  # 56 px di pratinjau = 224 px di asli
    nx, ny = (w.titik[2] * 4).astype(int)
    tepi = asli.load()
    for i in range(-6, 7):
        for j in range(-6, 7):
            tepi[int(nx) + i, int(ny) + j] = (255, 255, 255)
    rec = RecPalsu()
    diminta = []

    def ambil(sisi):
        diminta.append(sisi)
        return asli

    h = pipa_wajah.proses_foto(pratinjau, ambil, DetPalsu([w]), rec)
    assert diminta == [2048]
    ys, xs = np.nonzero(np.asarray(rec.terima[0]).sum(2) > 300)
    assert abs(xs.mean() - TEMPLAT_112[2, 0]) <= 1.5 and abs(ys.mean() - TEMPLAT_112[2, 1]) <= 1.5
    assert h[0][6] == pytest.approx(224)


def _tanda(gambar, x, y):
    px = gambar.load()
    for i in range(-6, 7):
        for j in range(-6, 7):
            px[int(x) + i, int(y) + j] = (255, 255, 255)


def _lihat_hidung(lebar):
    """Detektor potongan yang menemukan hidung sebenarnya (tanda putih) di potongan."""
    def halus(pot):
        ys, xs = np.nonzero(np.asarray(pot).sum(2) > 300)
        hidung = np.array([xs.mean(), ys.mean()])
        titik = (TEMPLAT_112 - TEMPLAT_112[2]) * (lebar / 112) + hidung
        pusat = titik.mean(0)
        return [Wajah(np.array([*(pusat - lebar / 2), *(pusat + lebar / 2)], np.float32), titik.astype(np.float32), 0.9)]

    return halus


def test_titik_dihaluskan_dari_potongan_foto_asli():
    pratinjau = Image.new("RGB", (1024, 512))
    asli = Image.new("RGB", (4096, 2048))
    w = wajah_di(100, 100, 56)
    kasar = w.titik[2] * 4
    _tanda(asli, kasar[0] + 14, kasar[1] - 10)  # hidung sebenarnya meleset dari titik kasar
    rec, det = RecPalsu(), DetPalsu([w], _lihat_hidung(224))
    pipa_wajah.proses_foto(pratinjau, lambda sisi: asli, det, rec)
    ys, xs = np.nonzero(np.asarray(rec.terima[0]).sum(2) > 300)
    assert abs(xs.mean() - TEMPLAT_112[2, 0]) <= 1.5 and abs(ys.mean() - TEMPLAT_112[2, 1]) <= 1.5
    ukuran, sisi = det.panggilan[1]
    assert sisi == pipa_wajah.SISI_HALUS and 440 <= ukuran[0] <= 500  # potongan 2,2 x lebar wajah dari foto asli


def test_wajah_besar_dihaluskan_dari_pratinjau():
    pratinjau = Image.new("RGB", (1024, 683))
    w = wajah_di(300, 200, 200)
    _tanda(pratinjau, w.titik[2][0] + 9, w.titik[2][1] + 7)
    rec = RecPalsu()
    pipa_wajah.proses_foto(pratinjau, None, DetPalsu([w], _lihat_hidung(200)), rec)
    ys, xs = np.nonzero(np.asarray(rec.terima[0]).sum(2) > 300)
    assert abs(xs.mean() - TEMPLAT_112[2, 0]) <= 1.5 and abs(ys.mean() - TEMPLAT_112[2, 1]) <= 1.5


def test_penghalusan_mengabaikan_wajah_tetangga():
    pratinjau = Image.new("RGB", (1024, 683))
    w = wajah_di(300, 200, 200)
    _tanda(pratinjau, w.titik[2][0], w.titik[2][1])

    def tetangga(pot):  # wajah lain di tepi potongan, lebih dari setengah lebar wajah dari pusat
        return [wajah_di(0, 0, 60)]

    rec = RecPalsu()
    pipa_wajah.proses_foto(pratinjau, None, DetPalsu([w], tetangga), rec)
    ys, xs = np.nonzero(np.asarray(rec.terima[0]).sum(2) > 300)
    assert abs(xs.mean() - TEMPLAT_112[2, 0]) <= 1.5  # titik kasar tetap dipakai


def test_penghalusan_memilih_wajah_terdekat_bukan_skor_tertinggi():
    pratinjau = Image.new("RGB", (1024, 683))
    w = wajah_di(300, 200, 200)
    benar = _lihat_hidung(200)

    def dua(pot):
        dekat = benar(pot)[0]
        dekat.skor = 0.5
        jauh = Wajah(dekat.kotak + 50, dekat.titik + 50, 0.99)  # tetangga rapat, masih di dalam radius
        return [jauh, dekat]

    _tanda(pratinjau, w.titik[2][0] + 5, w.titik[2][1] + 5)
    rec = RecPalsu()
    pipa_wajah.proses_foto(pratinjau, None, DetPalsu([w], dua), rec)
    ys, xs = np.nonzero(np.asarray(rec.terima[0]).sum(2) > 300)
    assert abs(xs.mean() - TEMPLAT_112[2, 0]) <= 1.5 and abs(ys.mean() - TEMPLAT_112[2, 1]) <= 1.5


def test_pratinjau_kecil_tidak_meminta_asli():
    def jangan(sisi):
        raise AssertionError("asli dibaca")

    h = pipa_wajah.proses_foto(Image.new("RGB", (640, 480)), jangan, DetPalsu([wajah_di(10, 10, 50)]), RecPalsu())
    assert len(h) == 1


def test_asli_tidak_tersedia_melempar_perlu_asli():
    def tidak_ada(sisi):
        return None

    with pytest.raises(pipa_wajah.PerluAsli):
        pipa_wajah.proses_foto(Image.new("RGB", (1024, 683)), tidak_ada, DetPalsu([wajah_di(10, 10, 50)]), RecPalsu())


def test_embedding_disimpan_float16_ternormalisasi():
    h = pipa_wajah.proses_foto(Image.new("RGB", (1024, 683)), None, DetPalsu([wajah_di(100, 100, 200)]), RecPalsu())
    v = np.frombuffer(h[0][10], np.float16)
    assert v.shape == (512,) and v[0] == 1


# --- pemindai wajah
@pytest.fixture
def ctx(tmp_path):
    akar = tmp_path / "foto"
    akar.mkdir()
    c = db.buka(tmp_path / "a.db")
    sid = library.tambah_sumber(c, str(akar))
    return akar, c, sid, tmp_path / "thumbs"


def isi_foto(c, sid, sha, taken=100, rel=None):
    c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) "
              "VALUES (?,?,1,1,?,100,100,?,'ok')", (sid, rel or f"{sha}.jpg", sha, taken))
    c.commit()


def pemindai(ctx):
    import pembantu_wajah

    _, c, _, th = ctx
    return pipa_wajah.PemindaiWajah(c, th, olah=pembantu_wajah.olah_palsu, muat=pembantu_wajah.muat_palsu)


def status(c):
    return c.execute("SELECT sha1, wajah_model, (SELECT count(*) FROM face f WHERE f.photo_id=p.id) "
                     "FROM photo p ORDER BY sha1").fetchall()


M = pipa_wajah.MODEL


def test_foto_diproses_dan_wajah_tersimpan(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "aa" * 20)
    isi_foto(c, sid, "bb" * 20)
    r = pemindai(ctx).jalankan()
    assert (r.selesai, r.wajah) == (2, 2)
    assert status(c) == [("aa" * 20, M, 2), ("bb" * 20, M, 0)]


def test_pindai_lanjutan_tidak_mengulang(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "aa" * 20)
    pemindai(ctx).jalankan()
    assert pemindai(ctx).jalankan().selesai == 0


def test_batas_memungkinkan_lanjut_nanti(ctx):
    _, c, sid, _ = ctx
    for s in ("aa", "bb", "ff"):
        isi_foto(c, sid, s * 20)
    assert pemindai(ctx).jalankan(batas=1).selesai == 1
    assert pemindai(ctx).jalankan().selesai == 2


def test_terbaru_lebih_dulu(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "bb" * 20, taken=1)
    isi_foto(c, sid, "aa" * 20, taken=9)
    pemindai(ctx).jalankan(batas=1)
    assert status(c)[0][1] == M and status(c)[1][1] is None


def test_drive_tak_ada_foto_butuh_asli_dicoba_lagi(ctx):
    akar, c, sid, _ = ctx
    isi_foto(c, sid, "cc" * 20)
    os.rename(akar, str(akar) + "_x")
    r = pemindai(ctx).jalankan()
    assert (r.selesai, r.menunggu_drive) == (0, 1)
    assert status(c)[0][1] is None
    os.rename(str(akar) + "_x", akar)
    assert pemindai(ctx).jalankan().selesai == 1


def test_pekerja_mati_lanjut_dan_dicatat(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "aa" * 20, taken=9)
    isi_foto(c, sid, "dd" * 20, taken=5)
    isi_foto(c, sid, "ff" * 20, taken=1)
    r = pemindai(ctx).jalankan()
    assert r.selesai == 2 and r.gagal == 1
    baris = c.execute("SELECT sha1, wajah_galat IS NOT NULL FROM photo ORDER BY sha1").fetchall()
    assert baris == [("aa" * 20, 0), ("dd" * 20, 1), ("ff" * 20, 0)]
    assert status(c)[2][2] == 1


def test_foto_gagal_dicatat_tidak_diulang(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "ee" * 20)
    r = pemindai(ctx).jalankan()
    assert r.gagal == 1
    assert pemindai(ctx).jalankan().selesai == 0


def test_batal_menghentikan(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "aa" * 20)
    e = threading.Event()
    e.set()
    r = pemindai(ctx).jalankan(batal=e)
    assert r.dibatalkan and r.selesai == 0


def test_hanya_foto_ok(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "aa" * 20)
    c.execute("UPDATE photo SET status='hilang'")
    c.commit()
    assert pemindai(ctx).jalankan().selesai == 0


def test_tugas_memakai_jalur_thumbnail_dan_asli(ctx):
    akar, c, sid, th = ctx
    isi_foto(c, sid, "aa" * 20, rel="sub/x.jpg")
    t = pemindai(ctx)._tugas(c.execute("SELECT id, source_id, rel, sha1, ukuran, mtime_ns FROM photo").fetchone(), {sid: str(akar)})
    assert t == (str(thumbs.jalur(th, "aa" * 20, thumbs.BESAR)), os.path.join(str(akar), "sub\\x.jpg"), 1, 1)


# --- migrasi dan kaitan dengan pemindai foto
def test_migrasi_v1_ke_v2_menjaga_data(tmp_path):
    import sqlite3

    p = tmp_path / "a.db"
    c = sqlite3.connect(p)
    c.executescript(db.MIGRASI[0])
    c.execute("PRAGMA user_version=1")
    c.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'s','x','E:','l')")
    c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, status) VALUES (1,'a.jpg',1,1,'ok')")
    c.commit()
    c.close()
    c = db.buka(p)
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.VERSI >= 2
    assert c.execute("SELECT rel, wajah_model FROM photo").fetchall() == [("a.jpg", None)]


def buat_foto(p, warna=(200, 10, 10), ukuran=(640, 480)):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", ukuran, warna).save(p, "JPEG")


def beri_wajah(c):
    pid = c.execute("SELECT id FROM photo").fetchone()[0]
    c.execute("UPDATE photo SET wajah_model=?", (M,))
    c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model) "
              "VALUES (?,0,0,1,1,x'00',1,1,1,1,1,x'00',?)", (pid, M))
    c.commit()
    return pid


def test_isi_berubah_membuang_wajah(ctx):
    akar, c, sid, th = ctx
    buat_foto(akar / "a.jpg")
    scanner.Pemindai(c, th, pekerja=1).jalankan(sid)
    beri_wajah(c)
    buat_foto(akar / "a.jpg", warna=(1, 200, 9), ukuran=(300, 300))
    os.utime(akar / "a.jpg", (1, 1))
    scanner.Pemindai(c, th, pekerja=1).jalankan(sid)
    assert c.execute("SELECT count(*) FROM face").fetchone()[0] == 0
    assert c.execute("SELECT wajah_model FROM photo").fetchone()[0] is None


def test_pindah_menjaga_wajah(ctx):
    akar, c, sid, th = ctx
    buat_foto(akar / "a.jpg")
    scanner.Pemindai(c, th, pekerja=1).jalankan(sid)
    pid = beri_wajah(c)
    os.replace(akar / "a.jpg", akar / "b.jpg")
    scanner.Pemindai(c, th, pekerja=1).jalankan(sid)
    assert c.execute("SELECT photo_id FROM face").fetchall() == [(pid,)]
    assert c.execute("SELECT wajah_model FROM photo").fetchone()[0] == M


def test_model_nyata_tanpa_wajah(tmp_path):
    akar = Path(__file__).resolve().parents[2] / "models" / "buffalo_l"
    if not (akar / "w600k_r50.onnx").exists():
        pytest.skip("model belum diunduh")
    det = faces.Detektor(akar / "det_10g.onnx", 2)
    rec = faces.Pengenal(akar / "w600k_r50.onnx", 2)
    assert pipa_wajah.proses_foto(Image.new("RGB", (1024, 683), (120, 130, 140)), None, det, rec) == []


# --- hasil review
def test_pekerja_termuat_bisa_membuka_heic(tmp_path):
    from concurrent.futures import ProcessPoolExecutor

    import pembantu_wajah
    import pillow_heif

    m = Path(__file__).resolve().parents[2] / "models" / "buffalo_l"
    if not (m / "w600k_r50.onnx").exists():
        pytest.skip("model belum diunduh")
    p = tmp_path / "a.heic"
    pillow_heif.register_heif_opener()
    Image.new("RGB", (128, 96), (9, 9, 9)).save(p, "HEIF")
    with ProcessPoolExecutor(1, initializer=pipa_wajah.muat, initargs=(str(m / "det_10g.onnx"), str(m / "w600k_r50.onnx"), 1, None, "ort")) as pool:
        assert max(pool.submit(pembantu_wajah.buka_asli, str(p)).result()) >= 64


def test_pekerja_mati_sekali_tidak_menghukum_foto(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "ab" * 20)
    r = pemindai(ctx).jalankan()
    assert (r.selesai, r.gagal) == (1, 0)
    assert status(c)[0][1:] == (M, 1)


def test_pekerja_selalu_mati_tidak_menandai_seluruh_pustaka(ctx):
    _, c, sid, _ = ctx
    for i in range(8):
        isi_foto(c, sid, "dd" * 19 + f"{i:02x}")
    r = pemindai(ctx).jalankan()
    assert r.galat_sistem and r.selesai == 0
    assert pipa_wajah.jumlah_belum(c) == 8


def test_pratinjau_hilang_bukan_kegagalan_permanen(tmp_path):
    with pytest.raises(OSError) as e:
        pipa_wajah.olah_foto((str(tmp_path / "tidak_ada.jpg"), None, 1, 1))
    assert e.value.errno is not None


def test_pratinjau_rusak_gagal_permanen(tmp_path):
    p = tmp_path / "a.jpg"
    p.write_bytes(b"bukan gambar")
    with pytest.raises(pipa_wajah.GagalWajah):
        pipa_wajah.olah_foto((str(p), None, 1, 1))


def test_asli_terkunci_dicoba_lagi(tmp_path):
    d = tmp_path / "folder.jpg"
    d.mkdir()  # membuka folder sebagai file: PermissionError, galat lingkungan seperti file terkunci
    st = d.stat()
    assert pipa_wajah._pengambil(str(d), st.st_size, st.st_mtime_ns)(64) is None


def test_asli_rusak_tetap_galat(tmp_path):
    p = tmp_path / "a.jpg"
    p.write_bytes(b"bukan gambar")
    st = p.stat()
    with pytest.raises(OSError) as e:
        pipa_wajah._pengambil(str(p), st.st_size, st.st_mtime_ns)(64)
    assert e.value.errno is None


def test_asli_berubah_sejak_pindai_tidak_dipakai(tmp_path):
    p = tmp_path / "a.jpg"
    Image.new("RGB", (64, 64)).save(p, "JPEG")
    st = p.stat()
    assert pipa_wajah._pengambil(str(p), st.st_size + 1, st.st_mtime_ns)(64) is None
    assert pipa_wajah._pengambil(str(p), st.st_size, st.st_mtime_ns + 1)(64) is None
    assert pipa_wajah._pengambil(str(p), st.st_size, st.st_mtime_ns)(64) is not None


def test_asli_beda_rasio_ditolak():
    with pytest.raises(pipa_wajah.PerluAsli):
        pipa_wajah.proses_foto(Image.new("RGB", (1024, 768)), lambda s: Image.new("RGB", (3000, 4000)),
                               DetPalsu([wajah_di(10, 10, 50)]), RecPalsu())


def test_gagal_di_model_baru_membuang_wajah_lama(ctx):
    _, c, sid, _ = ctx
    isi_foto(c, sid, "ee" * 20)
    pid = c.execute("SELECT id FROM photo").fetchone()[0]
    c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model) "
              "VALUES (?,0,0,1,1,x'00',1,1,1,1,1,x'00','lama')", (pid,))
    c.commit()
    pemindai(ctx).jalankan()
    assert c.execute("SELECT count(*) FROM face").fetchone()[0] == 0


def test_mengimpor_antarmuka_tidak_memuat_onnxruntime():
    import subprocess

    app = Path(__file__).resolve().parents[2] / "app"
    kode = f"import sys; sys.path.insert(0, {str(app)!r}); import ui.bridge.pindai; assert 'onnxruntime' not in sys.modules"
    r = subprocess.run([sys.executable, "-c", kode], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_migrasi_gagal_tidak_setengah_jadi(tmp_path, monkeypatch):
    p = tmp_path / "a.db"
    db.buka(p).close()
    asli = db.MIGRASI
    monkeypatch.setattr(db, "MIGRASI", [*asli, "ALTER TABLE photo ADD COLUMN coba TEXT; INI BUKAN SQL;"])
    with pytest.raises(Exception):
        db.buka(p)
    monkeypatch.setattr(db, "MIGRASI", [*asli, "ALTER TABLE photo ADD COLUMN coba TEXT;"])
    c = db.buka(p)
    assert c.execute("PRAGMA user_version").fetchone()[0] == len(asli) + 1


# --- mesin hitung: OpenVINO bila ada, ONNX Runtime sebagai cadangan
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "buffalo_l"


def _gambar_wajah():
    g = np.random.default_rng(4).integers(0, 255, (480, 640, 3), np.uint8)
    return Image.fromarray(g)


def test_mesin_bawaan_memilih_yang_tersedia(monkeypatch):
    monkeypatch.setattr(faces, "_openvino", lambda: None)
    assert faces.pilih_alat() == "ort"


def test_openvino_gagal_jatuh_ke_onnx_runtime(monkeypatch):
    def rusak(*a, **k):
        raise RuntimeError("driver GPU bermasalah")

    monkeypatch.setattr(faces, "SesiOpenVINO", rusak)
    sesi = faces.buat_sesi(MODEL_DIR / "w600k_r50.onnx", 1, alat="GPU")
    assert faces.nama_mesin(sesi) == "ort"


@pytest.mark.skipif(faces._openvino() is None, reason="OpenVINO tidak terpasang")
def test_ukuran_kumpulan_tidak_berlaku_untuk_detektor(tmp_path, monkeypatch):
    # keluaran SCRFD meratakan kumpulan: detektor yang diisi nol sampai ukuran kumpulan merusak penguraiannya
    monkeypatch.setattr(faces, "BUCKET", (2, 4))
    det = faces.Detektor(MODEL_DIR / "det_10g.onnx", 2, alat="CPU", cache=str(tmp_path))
    acuan = faces.Detektor(MODEL_DIR / "det_10g.onnx", 2, alat="ort")
    blob = np.random.default_rng(6).uniform(-1, 1, (1, 3, 192, 192)).astype(np.float32)
    x, y = acuan.sesi.run(None, {acuan.masuk: blob}), det.sesi.run(None, {det.masuk: blob})
    assert all(p.shape == q.shape and np.allclose(p, q, atol=1e-3) for p, q in zip(x, y))


@pytest.mark.skipif(faces._openvino() is None, reason="OpenVINO tidak terpasang")
def test_openvino_cpu_sama_dengan_onnx_runtime(tmp_path):
    ort_rec = faces.Pengenal(MODEL_DIR / "w600k_r50.onnx", 2, alat="ort")
    ov_rec = faces.Pengenal(MODEL_DIR / "w600k_r50.onnx", 2, alat="CPU", cache=str(tmp_path))
    assert faces.nama_mesin(ov_rec.sesi) == "openvino-CPU"
    wajah = [wajah_acak(), wajah_acak().rotate(5), wajah_acak().rotate(-5)]
    a, b = ort_rec.embed(wajah), ov_rec.embed(wajah)
    assert a.shape == b.shape == (3, 512) and (a * b).sum(1).min() > 0.999
    assert ov_rec.embed(wajah[:1]).shape == (1, 512)
    # semua ukuran kumpulan disiapkan saat dimuat: kompilasi di tengah pekerjaan memperlambat foto pertama tiap ukuran
    assert len(ov_rec.sesi._kompilasi) == len(faces.BUCKET)
    banyak = [wajah_acak().rotate(i) for i in range(11)]  # lebih dari kumpulan terbesar: dipecah, sisanya diisi nol
    assert (ov_rec.embed(banyak) * ort_rec.embed(banyak)).sum(1).min() > 0.999

    ort_det = faces.Detektor(MODEL_DIR / "det_10g.onnx", 2, alat="ort")
    ov_det = faces.Detektor(MODEL_DIR / "det_10g.onnx", 2, alat="CPU", cache=str(tmp_path))
    assert set(ov_det.sesi._kompilasi) == {(1, 3, 640, 640), (1, 3, pipa_wajah.SISI_HALUS, pipa_wajah.SISI_HALUS)}
    acak = np.random.default_rng(5)
    for sisi in (640, 192):  # keluaran mentah ke-9 tensor, urutannya harus sama
        blob = acak.uniform(-1, 1, (1, 3, sisi, sisi)).astype(np.float32)
        x = ort_det.sesi.run(None, {ort_det.masuk: blob})
        y = ov_det.sesi.run(None, {ov_det.masuk: blob})
        assert len(x) == len(y) == 9 and all(np.allclose(p, q, atol=1e-3) for p, q in zip(x, y))
