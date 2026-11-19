import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core import db, kelompok, orang
from core.pipa_wajah import MODEL

ACAK = np.random.default_rng(3)


def pusat():
    v = ACAK.standard_normal(512)
    return v / np.linalg.norm(v)


def dekat(c, s=0.03):
    v = c + ACAK.normal(0, s, 512)
    return v / np.linalg.norm(v)


@pytest.fixture
def c(tmp_path):
    k = db.buka(tmp_path / "a.db")
    k.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'','x','C:','x')")
    k.commit()
    return k


_n = [0]


def foto(c):
    _n[0] += 1
    return c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) "
                     "VALUES (1,?,1,1,?,100,100,1,'ok')", (f"{_n[0]}.jpg", f"{_n[0]:040x}")).lastrowid


def wajah(c, v, photo=None, lebar=120.0, kualitas=0.8):
    return c.execute("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, embedding, model) "
                     "VALUES (?,0.1,0.1,0.3,0.3,x'00',0.9,?,300,0.9,?,?,?)",
                     (photo or foto(c), lebar, kualitas, v.astype(np.float16).tobytes(), MODEL)).lastrowid


def orang_dari(c, face_id):
    return c.execute("SELECT person_id FROM face WHERE id=?", (face_id,)).fetchone()[0]


def banyak(c, p, n, **kw):
    return [wajah(c, dekat(p), **kw) for _ in range(n)]


def jumlah_orang(c):
    return c.execute("SELECT count(*) FROM person").fetchone()[0]


# --- pengelompokan
def test_tetangga_menemukan_yang_terdekat():
    a, b = pusat(), pusat()
    V = np.stack([dekat(a), dekat(a), dekat(b), dekat(b)], dtype=np.float32)
    idx, skor = kelompok.tetangga(V, 1, blok=2)
    assert idx[:, 0].tolist() == [1, 0, 3, 2]
    assert (skor[:, 0] > 0.4).all()


def test_tiga_orang_terpisah_bersih(c):
    kel = [banyak(c, pusat(), 8) for _ in range(3)]
    kelompok.kelompokkan(c)
    assert jumlah_orang(c) == 3
    for anggota in kel:
        assert len({orang_dari(c, f) for f in anggota}) == 1


def test_dua_wajah_satu_foto_tidak_sekelompok(c):
    p = pusat()
    bersama = foto(c)
    a, b = wajah(c, dekat(p), bersama), wajah(c, dekat(p), bersama)
    banyak(c, p, 6)
    kelompok.kelompokkan(c)
    assert not (orang_dari(c, a) and orang_dari(c, a) == orang_dari(c, b))


def test_wajah_penghubung_tidak_menggabungkan(c):
    pa, pb = pusat(), pusat()
    a, b = banyak(c, pa, 10), banyak(c, pb, 10)
    tengah = (pa + pb) / np.linalg.norm(pa + pb)
    wajah(c, tengah)
    kelompok.kelompokkan(c)
    assert orang_dari(c, a[0]) != orang_dari(c, b[0])
    assert jumlah_orang(c) == 2


def test_kelompok_terlalu_kecil_belum_jadi_orang(c):
    a = banyak(c, pusat(), 2)
    kelompok.kelompokkan(c)
    assert jumlah_orang(c) == 0
    assert c.execute("SELECT state FROM face WHERE id=?", (a[0],)).fetchone()[0] == "belum"


def test_wajah_kualitas_rendah_tidak_membentuk_kelompok(c):
    banyak(c, pusat(), 6, lebar=20.0)
    kelompok.kelompokkan(c)
    assert jumlah_orang(c) == 0


def test_wajah_kualitas_rendah_dilampirkan_bila_sangat_mirip(c):
    p = pusat()
    banyak(c, p, 8)
    kecil = wajah(c, dekat(p, 0.015), lebar=30.0)
    kelompok.kelompokkan(c)
    assert orang_dari(c, kecil) is not None


def test_prototipe_menjaga_dua_rupa():
    a, b = pusat(), pusat()
    V = np.stack([dekat(a) for _ in range(6)] + [dekat(b) for _ in range(6)], dtype=np.float32)
    P = kelompok.prototipe(V, np.ones(12), 5)
    assert 2 <= len(P) <= 5
    assert (P @ a).max() > 0.7 and (P @ b).max() > 0.7


def test_wajah_baru_ditugaskan_ke_orang_lama(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    pid = orang_dari(c, a[0])
    baru = wajah(c, dekat(p))
    r = kelompok.kelompokkan(c)
    assert orang_dari(c, baru) == pid and r.ditugaskan == 1 and jumlah_orang(c) == 1


def test_wajah_ragu_antara_dua_orang_tidak_ditugaskan(c):
    pa, pb = pusat(), pusat()
    banyak(c, pa, 8)
    banyak(c, pb, 8)
    kelompok.kelompokkan(c)
    tengah = (pa + pb) / np.linalg.norm(pa + pb)
    ragu = wajah(c, dekat(tengah, 0.005))
    kelompok.kelompokkan(c)
    assert orang_dari(c, ragu) is None


def test_pengelompokan_tidak_mengambil_anggota_orang_lain(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    pid = orang_dari(c, a[0])
    orang.beri_nama(c, pid, "Budi")
    kelompok.kelompokkan(c)
    assert {orang_dari(c, f) for f in a} == {pid}


# --- tindakan pemilik
def siap(c, n=8):
    p = pusat()
    a = banyak(c, p, n)
    kelompok.kelompokkan(c)
    return p, a, orang_dari(c, a[0])


def test_bukan_dia_bertahan_setelah_kelompok_ulang(c):
    p, a, pid = siap(c)
    orang.bukan_dia(c, [a[0]], pid)
    assert orang_dari(c, a[0]) is None
    kelompok.kelompokkan(c)
    assert orang_dari(c, a[0]) != pid


def test_nama_ganda_menggabungkan_kelompok(c):
    _, a, p1 = siap(c)
    _, b, p2 = siap(c)
    orang.beri_nama(c, p1, "Sari")
    hasil = orang.beri_nama(c, p2, "  sari ")
    assert hasil == p1
    assert orang_dari(c, b[0]) == p1 and jumlah_orang(c) == 1
    assert c.execute("SELECT nama FROM person").fetchone()[0] == "Sari"


def test_nama_kosong_ditolak(c):
    _, _, p = siap(c)
    with pytest.raises(ValueError):
        orang.beri_nama(c, p, "   ")


def test_gabung_mempertahankan_nama(c):
    _, a, p1 = siap(c)
    _, b, p2 = siap(c)
    orang.beri_nama(c, p2, "Rina")
    orang.gabung(c, p2, p1)
    assert jumlah_orang(c) == 1
    assert c.execute("SELECT nama FROM person WHERE id=?", (p1,)).fetchone()[0] == "Rina"
    assert orang_dari(c, b[0]) == p1


def test_semua_wajah_dikeluarkan_orang_hilang(c):
    _, a, pid = siap(c)
    orang.bukan_dia(c, a, pid)
    assert jumlah_orang(c) == 0


def test_pisahkan_membuat_orang_baru_yang_bertahan(c):
    _, a, pid = siap(c)
    baru = orang.pisahkan(c, a[:3], pid, "Andi")
    assert baru != pid and {orang_dari(c, f) for f in a[:3]} == {baru}
    kelompok.kelompokkan(c)
    assert {orang_dari(c, f) for f in a[:3]} == {baru}
    assert {orang_dari(c, f) for f in a[3:]} == {pid}


def test_tetapkan_mengalahkan_bukan_dia_lama(c):
    _, a, pid = siap(c)
    orang.bukan_dia(c, [a[0]], pid)
    orang.tetapkan(c, [a[0]], pid)
    assert orang_dari(c, a[0]) == pid
    orang_lain = c.execute("SELECT count(*) FROM batasan WHERE jenis='beda' AND (face_a=? OR face_b=?)", (a[0], a[0])).fetchone()[0]
    assert orang_lain == 0


def test_batasan_hilang_bersama_foto(c):
    _, a, pid = siap(c)
    orang.bukan_dia(c, [a[0]], pid)
    assert c.execute("SELECT count(*) FROM batasan").fetchone()[0] > 0
    c.execute("DELETE FROM photo")
    c.commit()
    assert c.execute("SELECT count(*) FROM batasan").fetchone()[0] == 0


def test_antrean_terbanyak_dulu_tanpa_yang_bernama_atau_tersembunyi(c):
    _, _, kecil = siap(c, 5)
    _, _, besar = siap(c, 9)
    _, _, bernama = siap(c, 7)
    _, _, sembunyi = siap(c, 6)
    orang.beri_nama(c, bernama, "X")
    orang.sembunyikan(c, sembunyi)
    assert orang.antrean(c) == [besar, kecil]


def test_daftar_menghitung_foto_bukan_wajah(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    d = orang.daftar(c)
    assert len(d) == 1 and d[0]["jumlah"] == 8 and d[0]["nama"] is None


def test_foto_hilang_tidak_dihitung(c):
    _, a, _ = siap(c)
    c.execute("UPDATE photo SET status='hilang' WHERE id=(SELECT photo_id FROM face WHERE id=?)", (a[0],))
    c.commit()
    assert orang.daftar(c)[0]["jumlah"] == 7


def test_saran_menemukan_kelompok_terdekat(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    p2 = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    c.executemany("UPDATE face SET person_id=? WHERE id=?", [(p2, f) for f in a[:4]])
    c.commit()
    s = orang.saran(c, p1)
    assert s["id"] == p2 and s["pita"] in ("Sangat mirip", "Mirip", "Agak mirip")


def test_saran_tidak_menawarkan_yang_sudah_dipisah(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    orang.pisahkan(c, a[:4], p1, None)
    assert orang.saran(c, p1) is None


def test_saran_tanpa_kandidat(c):
    _, _, p1 = siap(c)
    assert orang.saran(c, p1) is None


def test_contoh_memuat_yang_terbaik_dan_yang_paling_jauh(c):
    p = pusat()
    a = banyak(c, p, 20)
    kelompok.kelompokkan(c)
    pid = orang_dari(c, a[0])
    aneh = wajah(c, dekat(p, 0.055))
    c.execute("UPDATE face SET person_id=? WHERE id=?", (pid, aneh))
    c.commit()
    ids = [w["id"] for w in orang.contoh(c, pid, 12)]
    assert len(ids) == 12 and len(set(ids)) == 12 and aneh in ids


# --- hasil review
def test_saran_mengabaikan_orang_yang_fotonya_hilang(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    p2 = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    c.executemany("UPDATE face SET person_id=? WHERE id=?", [(p2, f) for f in a[:4]])
    c.execute("UPDATE photo SET status='hilang' WHERE id IN (SELECT photo_id FROM face WHERE person_id=?)", (p2,))
    c.commit()
    assert orang.saran(c, p1) is None


def test_saran_tidak_menawarkan_orang_di_foto_yang_sama(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    p2 = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    c.executemany("UPDATE face SET person_id=? WHERE id=?", [(p2, f) for f in a[:4]])
    ph = c.execute("SELECT photo_id FROM face WHERE id=?", (a[5],)).fetchone()[0]
    f = wajah(c, dekat(p), ph)
    c.execute("UPDATE face SET person_id=? WHERE id=?", (p2, f))
    c.commit()
    assert orang.saran(c, p1) is None


def _sela(monkeypatch, tindakan):
    asli = kelompok._tugaskan
    sudah = []

    def sela(*a, **k):
        hasil = asli(*a, **k)
        if not sudah:
            sudah.append(1)
            tindakan()
        return hasil

    monkeypatch.setattr(kelompok, "_tugaskan", sela)


def test_orang_digabung_saat_mengelompokkan_tidak_galat(c, monkeypatch):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    p2 = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    c.execute("UPDATE face SET person_id=? WHERE id=?", (p2, a[7]))
    c.commit()
    baru = wajah(c, dekat(p))
    _sela(monkeypatch, lambda: orang.gabung(c, p1, p2))
    kelompok.kelompokkan(c)
    assert orang_dari(c, baru) is None
    monkeypatch.undo()
    kelompok.kelompokkan(c)
    assert orang_dari(c, baru) == p2


def test_koreksi_saat_mengelompokkan_tidak_tertimpa(c, monkeypatch):
    pa, pb = pusat(), pusat()
    a, b = banyak(c, pa, 8), banyak(c, pb, 8)
    kelompok.kelompokkan(c)
    p1, p2 = orang_dari(c, a[0]), orang_dari(c, b[0])
    baru = wajah(c, dekat(pa))
    _sela(monkeypatch, lambda: orang.tetapkan(c, [baru], p2))
    kelompok.kelompokkan(c)
    assert orang_dari(c, baru) == p2


def test_id_orang_terhapus_tidak_terpakai_ulang_oleh_kelompok_baru(c, monkeypatch):
    pa, pb = pusat(), pusat()
    a = banyak(c, pa, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    tambahan = wajah(c, dekat(pa))
    b = banyak(c, pb, 8)
    _sela(monkeypatch, lambda: orang.bukan_dia(c, a, p1))
    kelompok.kelompokkan(c)
    assert orang_dari(c, tambahan) is None
    assert orang_dari(c, b[0]) is not None


def test_wajah_terkoreksi_tetap_yakin_setelah_kelompok_ulang(c):
    _, a, pid = siap(c)
    orang.pisahkan(c, a[:3], pid, "Andi")
    kelompok.kelompokkan(c)
    assert c.execute("SELECT state FROM face WHERE id=?", (a[0],)).fetchone()[0] == "yakin"


def test_pisahkan_sedikit_wajah_tetap_terlihat(c):
    _, a, pid = siap(c)
    baru = orang.pisahkan(c, a[:1], pid, None)
    assert baru in [d["id"] for d in orang.daftar(c)]


def test_pisahkan_semua_wajah_menjaga_nama(c):
    _, a, pid = siap(c)
    orang.beri_nama(c, pid, "Budi")
    baru = orang.pisahkan(c, a, pid, None)
    assert c.execute("SELECT nama FROM person WHERE id=?", (baru,)).fetchone()[0] == "Budi"


def test_bukan_dia_bertahan_walau_jangkar_pergi(c):
    p = pusat()
    a = banyak(c, p, 14)
    kelompok.kelompokkan(c)
    pid = orang_dari(c, a[0])
    orang.bukan_dia(c, [a[9]], pid)
    orang.bukan_dia(c, a[:5], pid)
    kelompok.kelompokkan(c)
    assert orang_dari(c, a[9]) != pid


def test_orang_tanpa_wajah_dibersihkan_dan_namanya_hilang(c):
    _, a, pid = siap(c)
    orang.beri_nama(c, pid, "Budi")
    c.execute("DELETE FROM photo")
    c.commit()
    assert orang.nama_ada(c) == []
    kelompok.kelompokkan(c)
    assert jumlah_orang(c) == 0


def test_saran_memakai_pusat_tersimpan(c):
    p = pusat()
    a = banyak(c, p, 8)
    kelompok.kelompokkan(c)
    p1 = orang_dari(c, a[0])
    p2 = c.execute("INSERT INTO person(dibuat) VALUES (1)").lastrowid
    c.executemany("UPDATE face SET person_id=? WHERE id=?", [(p2, f) for f in a[:4]])
    c.commit()
    pusat_semua = orang.pusat_semua(c)
    assert orang.saran(c, p1, pusat_semua)["id"] == p2


# --- ambang dari data pustaka sendiri
def serupa(p, cos):
    """Pusat orang lain yang kemiripannya dengan `p` tepat `cos` (kerabat, teman sekelas berseragam)."""
    v = ACAK.standard_normal(512)
    v -= (v @ p) * p
    return cos * p + np.sqrt(1 - cos ** 2) * v / np.linalg.norm(v)


def test_kemiripan_satu_foto_hanya_pasangan_sefoto():
    V = np.eye(4, 512, dtype=np.float32)
    V[1] = V[0]
    k = kelompok.kemiripan_satu_foto(V, np.array([7, 7, 8, 9]), np.ones(4, bool))
    assert k.tolist() == [1.0]
    assert len(kelompok.kemiripan_satu_foto(V, np.array([7, 7, 8, 9]), np.array([True, False, True, True]))) == 0


def test_ambang_bawaan_bila_bukti_sedikit():
    assert kelompok.ambang_dari_data(np.full(10, 0.9)) == kelompok.AMBANG_TEPI


def test_ambang_naik_mengikuti_orang_yang_mirip_dan_dibatasi():
    assert kelompok.ambang_dari_data(np.full(500, 0.2)) == kelompok.AMBANG_TEPI
    tengah = kelompok.ambang_dari_data(np.concatenate([np.full(900, 0.2), np.full(100, 0.57)]))
    assert 0.57 < tengah < 0.62
    assert kelompok.ambang_dari_data(np.full(500, 0.9)) == kelompok.AMBANG_TEPI_MAKS


def test_orang_mirip_tidak_digabung_bila_pustaka_memang_berisi_orang_mirip(c):
    # 40 pasang orang mirip yang berfoto bersama: bukti bahwa kemiripan 0,5-an di pustaka ini belum berarti orang yang sama
    for _ in range(40):
        x = pusat()
        y = serupa(x, 0.55)
        for _ in range(3):
            f = foto(c)
            wajah(c, dekat(x, 0.01), f)
            wajah(c, dekat(y, 0.01), f)
    a = pusat()
    b = serupa(a, 0.55)
    wa, wb = banyak(c, a, 5), banyak(c, b, 5)
    c.commit()
    r = kelompok.kelompokkan(c)
    oa, ob = {orang_dari(c, i) for i in wa}, {orang_dari(c, i) for i in wb}
    assert len(oa) == 1 and len(ob) == 1 and None not in oa | ob and oa != ob
    assert r.ambang > 0.53


def test_tanpa_bukti_orang_mirip_ambang_tetap(c):
    banyak(c, pusat(), 5)
    c.commit()
    assert kelompok.kelompokkan(c).ambang == kelompok.AMBANG_TEPI


def test_ambang_mengabaikan_nilai_rusak():
    beda = np.concatenate([np.full(300, 0.2), [np.nan, np.inf]]).astype(np.float32)
    assert kelompok.ambang_dari_data(beda) == kelompok.AMBANG_TEPI


def test_beri_nama_mulai_dari_orang_yang_dipilih(c, tmp_path):
    from ui.bridge.orang import Orang

    besar, kecil = pusat(), pusat()
    for p_, n in ((besar, 6), (kecil, 3)):
        for _ in range(n):
            wajah(c, dekat(p_))
    c.commit()
    kelompok.kelompokkan(c)
    jalur = c.execute("PRAGMA database_list").fetchone()[2]
    o = Orang(jalur)
    o.mulaiTinjau()
    pertama = o.tinjau["id"]
    lain = next(d["id"] for d in o.daftar if d["id"] != pertama)
    o.mulaiTinjauDari(lain)
    assert o.tinjau["id"] == lain and o.tinjau["total"] == 2
    o.lewati()
    assert o.tinjau["id"] == pertama
