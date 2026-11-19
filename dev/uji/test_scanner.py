import os
import shutil
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core import db, library, scanner, thumbs


_jam = [1_600_000_000]


def buat_foto(p, warna=(200, 10, 10), ukuran=(640, 480), exif_tgl=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", ukuran, warna)
    if exif_tgl is None:
        im.save(p, "JPEG")
    else:
        ex = Image.Exif()
        ex.get_ifd(0x8769)[36867] = exif_tgl
        im.save(p, "JPEG", exif=ex)
    _jam[0] += 10  # dua file dalam satu tik jam Windows bisa sama ukuran dan waktunya
    os.utime(p, (_jam[0], _jam[0]))


@pytest.fixture
def ctx(tmp_path):
    akar = tmp_path / "foto"
    akar.mkdir()
    c = db.buka(tmp_path / "a.db")
    sid = library.tambah_sumber(c, str(akar))
    return akar, c, sid, tmp_path / "thumbs"


def pindai(ctx, **kw):
    akar, c, sid, th = ctx
    return scanner.Pemindai(c, th, pekerja=1).jalankan(sid, **kw)


def baris(c, kolom="rel, status"):
    return c.execute(f"SELECT {kolom} FROM photo ORDER BY rel").fetchall()


def test_pindai_menambah_foto_dan_thumbnail(ctx):
    akar, c, _, th = ctx
    buat_foto(akar / "a.jpg", exif_tgl="2021:03:04 05:06:07")
    r = pindai(ctx)
    assert r.baru == 1
    rel, sha, lebar, tinggi, sumber, st = baris(c, "rel, sha1, lebar, tinggi, sumber_tanggal, status")[0]
    assert (rel, lebar, tinggi, sumber, st) == ("a.jpg", 640, 480, "exif", "ok")
    assert thumbs.jalur(th, sha, 256).exists() and thumbs.jalur(th, sha, 1024).exists()


def test_tanggal_exif_tersimpan(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg", exif_tgl="2021:03:04 05:06:07")
    pindai(ctx)
    assert baris(c, "taken_at")[0][0] == 1614834367


def test_exif_rusak_jatuh_ke_tanggal_ubah(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg", exif_tgl="0000:00:00 00:00:00")
    pindai(ctx)
    assert baris(c, "sumber_tanggal, status")[0] == ("mtime", "ok")


def test_orientasi_exif_menukar_ukuran(ctx):
    akar, c, _, _ = ctx
    ex = Image.Exif()
    ex[0x0112] = 6
    Image.new("RGB", (640, 480)).save(akar / "a.jpg", "JPEG", exif=ex)
    pindai(ctx)
    assert baris(c, "lebar, tinggi")[0] == (480, 640)


def test_pindai_ulang_tanpa_perubahan(ctx):
    akar, _, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    r = pindai(ctx)
    assert (r.baru, r.berubah, r.gagal) == (0, 0, 0)


def test_file_berubah_diproses_ulang(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    lama = baris(c, "id, sha1")[0]
    buat_foto(akar / "a.jpg", warna=(1, 200, 9), ukuran=(300, 300))
    os.utime(akar / "a.jpg", (1, 1))
    r = pindai(ctx)
    baru = baris(c, "id, sha1")[0]
    assert r.berubah == 1 and baru[0] == lama[0] and baru[1] != lama[1]


def test_file_rusak_dicatat_dan_lanjut(ctx):
    akar, c, _, _ = ctx
    (akar / "a.jpg").write_bytes(b"bukan gambar")
    buat_foto(akar / "b.jpg")
    r = pindai(ctx)
    assert r.gagal == 1 and r.baru == 1
    assert baris(c) == [("a.jpg", "gagal"), ("b.jpg", "ok")]


def test_format_lain_dilewati(ctx):
    akar, c, _, _ = ctx
    (akar / "a.mp4").write_bytes(b"x")
    (akar / "a.cr2").write_bytes(b"x")
    r = pindai(ctx)
    assert baris(c) == [] and r.dilewati == 2


def test_folder_sistem_dilewati(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "_RapikanAlbum" / "x.jpg")
    buat_foto(akar / "$RECYCLE.BIN" / "x.jpg")
    buat_foto(akar / ".tersembunyi" / "x.jpg")
    pindai(ctx)
    assert baris(c) == []


def test_foto_dipindah_memakai_baris_lama(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    lama = baris(c, "id")[0][0]
    (akar / "sub").mkdir()
    shutil.move(akar / "a.jpg", akar / "sub" / "b.jpg")
    r = pindai(ctx)
    assert r.dipindah == 1
    assert baris(c, "id, rel, status") == [(lama, "sub/b.jpg", "ok")]


def test_foto_dihapus_ditandai_hilang_dan_kembali(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    simpan = (akar / "a.jpg").read_bytes()
    st = (akar / "a.jpg").stat()
    (akar / "a.jpg").unlink()
    assert pindai(ctx).hilang == 1
    assert baris(c) == [("a.jpg", "hilang")]
    (akar / "a.jpg").write_bytes(simpan)
    os.utime(akar / "a.jpg", ns=(st.st_atime_ns, st.st_mtime_ns))
    pindai(ctx)
    assert baris(c) == [("a.jpg", "ok")]


def test_drive_terlepas_tidak_menandai_hilang(ctx):
    akar, c, sid, th = ctx
    buat_foto(akar / "a.jpg")
    buat_foto(akar / "b.jpg")
    pindai(ctx)
    (akar / "b.jpg").unlink()
    buat_foto(akar / "c.jpg")
    asli = scanner.Pemindai._baca

    def baca_lalu_cabut(self, p):
        shutil.rmtree(akar)
        return asli(self, p)

    scanner.Pemindai._baca = baca_lalu_cabut
    try:
        r = scanner.Pemindai(c, th, pekerja=1).jalankan(sid)
    finally:
        scanner.Pemindai._baca = asli
    assert r.terputus
    assert {s for _, s in baris(c)} == {"ok"}


def test_akar_tidak_ada_tidak_menandai_hilang(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    shutil.rmtree(akar)
    assert pindai(ctx).terputus
    assert baris(c) == [("a.jpg", "ok")]


def test_folder_tak_terbaca_tidak_menandai_hilang(ctx, monkeypatch):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    (akar / "a.jpg").unlink()
    asli = scanner.temukan
    monkeypatch.setattr(scanner, "temukan", lambda a: (asli(a)[0], asli(a)[1], [""]))
    pindai(ctx)
    assert baris(c) == [("a.jpg", "ok")]


def test_batal_menghentikan(ctx):
    akar, c, _, _ = ctx
    for i in range(5):
        buat_foto(akar / f"{i}.jpg", warna=(i, 1, 1))
    e = threading.Event()
    e.set()
    r = pindai(ctx, batal=e)
    assert r.dibatalkan and r.baru == 0


def test_jeda_menunggu(ctx):
    akar, _, _, _ = ctx
    buat_foto(akar / "a.jpg")
    panggil = []

    def jeda():
        panggil.append(1)
        return len(panggil) < 3

    r = pindai(ctx, jeda=jeda)
    assert r.baru == 1 and len(panggil) >= 3


def test_semua_foto_terbaru_dulu_hanya_ok(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "lama.jpg", exif_tgl="2019:01:01 00:00:00")
    buat_foto(akar / "baru.jpg", warna=(0, 9, 0), exif_tgl="2022:01:01 00:00:00")
    (akar / "rusak.jpg").write_bytes(b"x")
    pindai(ctx)
    assert [Path(f.jalur_rel).name for f in library.semua_foto(c)] == ["baru.jpg", "lama.jpg"]


def test_tanggal_exif_tak_masuk_akal_jatuh_ke_mtime(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg", exif_tgl="9999:12:31 23:59:59")
    buat_foto(akar / "b.jpg", warna=(3, 3, 3), exif_tgl="0001:01:01 00:00:00")
    pindai(ctx)
    assert [b[0] for b in baris(c, "sumber_tanggal")] == ["mtime", "mtime"]


def test_pekerja_mati_hanya_menggagalkan_file_itu(ctx):
    import pembantu_scan

    akar, c, sid, th = ctx
    (akar / "b.jpg").write_bytes(b"MATI")
    buat_foto(akar / "a.jpg")
    buat_foto(akar / "c.jpg", warna=(0, 8, 0))
    r = scanner.Pemindai(c, th, pekerja=1, olah=pembantu_scan.olah_mati).jalankan(sid)
    assert r.baru == 2 and r.gagal == 1
    assert baris(c) == [("a.jpg", "ok"), ("b.jpg", "gagal"), ("c.jpg", "ok")]


def test_galat_sistem_tidak_menandai_foto_gagal(ctx):
    import pembantu_scan

    akar, c, sid, th = ctx
    buat_foto(akar / "a.jpg")
    r = scanner.Pemindai(c, th, pekerja=1, olah=pembantu_scan.olah_disk_penuh).jalankan(sid)
    assert r.galat_sistem and baris(c) == []
    assert pindai(ctx).baru == 1


def test_file_rusak_yang_dihapus_ikut_hilang(ctx):
    akar, c, _, _ = ctx
    (akar / "a.jpg").write_bytes(b"bukan gambar")
    pindai(ctx)
    (akar / "a.jpg").unlink()
    pindai(ctx)
    assert baris(c) == []


def test_jeda_tidak_menahan_tulis_sumber(ctx, tmp_path):
    import sqlite3

    akar, c, _, _ = ctx
    for i in range(5):
        buat_foto(akar / f"{i}.jpg", warna=(i, 2, 2))
    hitung = []
    galat = []

    def jeda():
        hitung.append(1)
        if len(hitung) == 5:
            return True
        if len(hitung) == 6:
            lain = sqlite3.connect(tmp_path / "a.db", timeout=0)
            try:
                lain.execute("UPDATE source SET label='x'")
                lain.commit()
            except sqlite3.OperationalError as e:
                galat.append(e)
            lain.close()
        return False

    pindai(ctx, jeda=jeda)
    assert galat == []


def test_folder_terkunci_tidak_menghalangi_deteksi_pindah(ctx, monkeypatch):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg")
    buat_foto(akar / "terkunci" / "b.jpg", warna=(0, 77, 0))
    pindai(ctx)
    id_a = dict(baris(c, "rel, id"))["a.jpg"]
    (akar / "sub").mkdir()
    shutil.move(akar / "a.jpg", akar / "sub" / "a2.jpg")
    (akar / "terkunci" / "b.jpg").unlink()
    asli = scanner.temukan
    monkeypatch.setattr(scanner, "temukan", lambda a: (asli(a)[0], asli(a)[1], ["terkunci"]))
    r = pindai(ctx)
    assert r.dipindah == 1 and r.folder_tak_terbaca == 1
    hasil = dict((b[0], b[1:]) for b in baris(c, "rel, id, status"))
    assert hasil["sub/a2.jpg"] == (id_a, "ok")
    assert hasil["terkunci/b.jpg"][1] == "ok"


def test_rantai_ganti_nama_menjaga_identitas(ctx):
    akar, c, _, _ = ctx
    for n, w in (("1", (9, 0, 0)), ("2", (0, 90, 0)), ("3", (0, 0, 200))):
        buat_foto(akar / f"{n}.jpg", warna=w, ukuran=(300 + int(n), 200))
    pindai(ctx)
    awal = {r: (i, s) for r, i, s in baris(c, "rel, id, sha1")}
    (akar / "1.jpg").unlink()
    os.replace(akar / "2.jpg", akar / "1.jpg")
    os.replace(akar / "3.jpg", akar / "2.jpg")
    r = pindai(ctx)
    assert r.dipindah == 2 and r.hilang == 1
    kini = {b[0]: b[1:] for b in baris(c, "rel, id, sha1, status")}
    assert kini["1.jpg"] == (*awal["2.jpg"], "ok")
    assert kini["2.jpg"] == (*awal["3.jpg"], "ok")
    assert [b for b in kini.values() if b[0] == awal["1.jpg"][0]][0][2] == "hilang"


def test_tukar_nama_menjaga_identitas(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a.jpg", warna=(9, 0, 0), ukuran=(301, 200))
    buat_foto(akar / "b.jpg", warna=(0, 90, 0), ukuran=(302, 200))
    pindai(ctx)
    awal = {r: i for r, i in baris(c, "rel, id")}
    os.replace(akar / "a.jpg", akar / "x")
    os.replace(akar / "b.jpg", akar / "a.jpg")
    os.replace(akar / "x", akar / "b.jpg")
    assert pindai(ctx).dipindah == 2
    assert {r: i for r, i in baris(c, "rel, id")} == {"a.jpg": awal["b.jpg"], "b.jpg": awal["a.jpg"]}


def test_foto_kembali_setelah_tergeser_memakai_baris_lama(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "1.jpg", warna=(9, 0, 0), ukuran=(301, 200))
    buat_foto(akar / "2.jpg", warna=(0, 90, 0), ukuran=(302, 200))
    pindai(ctx)
    id1 = dict(baris(c, "rel, id"))["1.jpg"]
    os.replace(akar / "1.jpg", akar.parent / "simpan.jpg")
    os.replace(akar / "2.jpg", akar / "1.jpg")
    pindai(ctx)
    os.replace(akar.parent / "simpan.jpg", akar / "lagi.jpg")
    assert pindai(ctx).dipindah == 1
    assert dict(baris(c, "rel, id"))["lagi.jpg"] == id1


def test_junction_tidak_ditelusuri(ctx, tmp_path):
    import _winapi

    akar, c, _, _ = ctx
    luar = tmp_path / "luar"
    buat_foto(luar / "x.jpg")
    _winapi.CreateJunction(str(luar), str(akar / "sambung"))
    pindai(ctx)
    assert baris(c) == []


def test_foto_pindah_folder_tidak_dibaca_ulang(ctx, monkeypatch):
    akar, c, _, _ = ctx
    for i in range(3):
        buat_foto(akar / "lama" / f"{i}.jpg", warna=(i * 60, 0, 0))
    pindai(ctx)
    sebelum = {rel.rsplit("/", 1)[-1]: i for rel, i in c.execute("SELECT rel, id FROM photo")}
    (akar / "baru" / "dalam").mkdir(parents=True)
    for i in range(3):
        shutil.move(akar / "lama" / f"{i}.jpg", akar / "baru" / "dalam" / f"{i}.jpg")

    def jangan(self, p):
        raise AssertionError("file dibaca ulang")

    monkeypatch.setattr(scanner.Pemindai, "_baca", jangan)
    r = pindai(ctx)
    assert (r.dipindah, r.baru, r.hilang) == (3, 0, 0)
    assert baris(c) == [(f"baru/dalam/{i}.jpg", "ok") for i in range(3)]
    assert {rel.rsplit("/", 1)[-1]: i for rel, i in c.execute("SELECT rel, id FROM photo")} == sebelum


def test_pindah_yang_tidak_pasti_dicocokkan_lewat_isi(ctx):
    akar, c, _, _ = ctx
    buat_foto(akar / "a" / "x.jpg")
    shutil.copy2(akar / "a" / "x.jpg", akar / "x.jpg")
    (akar / "b").mkdir()
    shutil.move(akar / "x.jpg", akar / "b" / "x.jpg")  # nama, ukuran, dan waktu sama dengan a/x.jpg
    pindai(ctx)
    ids = sorted(i for (i,) in c.execute("SELECT id FROM photo"))
    for asal, tujuan in (("a", "p"), ("b", "q")):
        (akar / tujuan).mkdir()
        shutil.move(akar / asal / "x.jpg", akar / tujuan / "x.jpg")
    r = pindai(ctx)
    assert (r.dipindah, r.baru, r.hilang) == (2, 0, 0)
    assert sorted(i for (i,) in c.execute("SELECT id FROM photo")) == ids


def test_sumber_dipindah_ke_folder_lain(ctx):
    akar, c, sid, _ = ctx
    buat_foto(akar / "x" / "a.jpg")
    pindai(ctx)
    baru = akar.parent / "tempat lain"
    shutil.move(akar, baru)
    assert library.akar_sumber(c, sid) is None
    assert scanner.cocok_lokasi(c, sid, str(baru)) == (1, 1)
    library.pindah_sumber(c, sid, str(baru))
    assert library.akar_sumber(c, sid) == str(baru)
    assert c.execute("SELECT label FROM source WHERE id=?", (sid,)).fetchone()[0] == "tempat lain"
    r = pindai(ctx)
    assert (r.baru, r.hilang, r.dipindah) == (0, 0, 0)


def test_lokasi_tanpa_foto_yang_dikenal(ctx, tmp_path):
    akar, c, sid, _ = ctx
    buat_foto(akar / "a.jpg")
    pindai(ctx)
    buat_foto(tmp_path / "asing" / "lain.jpg")
    assert scanner.cocok_lokasi(c, sid, str(tmp_path / "asing")) == (0, 1)


def test_pindah_sumber_ke_lokasi_sumber_lain_ditolak(ctx, tmp_path):
    akar, c, sid, _ = ctx
    lain = tmp_path / "lain"
    lain.mkdir()
    library.tambah_sumber(c, str(lain))
    with pytest.raises(ValueError):
        library.pindah_sumber(c, sid, str(lain))
