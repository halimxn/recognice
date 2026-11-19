import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from core import cadangan, db, ekspor, library  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def ctx(tmp_path):
    akar = tmp_path / "foto"
    (akar / "a").mkdir(parents=True)
    (akar / "b").mkdir()
    c = db.buka(tmp_path / "data" / "library.db")
    sid = library.tambah_sumber(c, str(akar))
    for rel, isi in (("a/x.jpg", b"satu"), ("b/x.jpg", b"dua22")):
        (akar / rel).write_bytes(isi)
        c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (?,?,?,1,'s',1,1,1,'ok')",
                  (sid, rel, len(isi)))
    c.commit()
    return tmp_path, akar, c


def test_ekspor_menyalin_tanpa_menimpa_dan_mencatat(ctx):
    tmp, akar, c = ctx
    tujuan = tmp / "keluar"
    tujuan.mkdir()
    (tujuan / "x.jpg").write_bytes(b"milik pemilik")
    r = ekspor.ekspor(c, None, str(tujuan), tmp / "jurnal")
    assert r.disalin == 2 and r.gagal == 0
    assert (tujuan / "x.jpg").read_bytes() == b"milik pemilik"
    assert sorted(p.read_bytes() for p in tujuan.glob("x_*.jpg")) == [b"dua22", b"satu"]
    assert (akar / "a/x.jpg").read_bytes() == b"satu"
    baris = [json.loads(b) for f in (tmp / "jurnal").glob("*.jsonl") for b in f.read_text(encoding="utf-8").splitlines()]
    assert [b["aksi"] for b in baris].count("selesai") == 2


def test_ekspor_ke_dalam_sumber_ditolak(ctx):
    tmp, akar, c = ctx
    with pytest.raises(ValueError):
        ekspor.ekspor(c, None, str(akar / "a"), tmp / "jurnal")


def test_ekspor_drive_tak_terhubung_dihitung(ctx):
    tmp, akar, c = ctx
    os.rename(akar, str(akar) + "_x")
    r = ekspor.ekspor(c, None, str(tmp / "keluar"), tmp / "jurnal")
    assert r.tak_terhubung == 2 and r.disalin == 0


def test_ekspor_file_hilang_gagal_tanpa_sisa(ctx):
    tmp, akar, c = ctx
    (akar / "a/x.jpg").unlink()
    r = ekspor.ekspor(c, None, str(tmp / "keluar"), tmp / "jurnal")
    assert (r.disalin, r.gagal) == (1, 1)
    assert not list((tmp / "keluar").glob("*.tmp"))


def test_cadangan_lalu_pulihkan(ctx):
    tmp, _, c = ctx
    data = tmp / "data"
    (data / "pengaturan.json").write_text("{}", encoding="utf-8")
    folder = cadangan.buat(data, tmp / "aman")
    assert (folder / "pengaturan.json").exists()
    c.execute("DELETE FROM photo")
    c.commit()
    c.close()
    cadangan.jadwalkan(data, folder)
    assert cadangan.terapkan_bila_ada(data)
    c2 = sqlite3.connect(data / "library.db")
    assert c2.execute("SELECT count(*) FROM photo").fetchone()[0] == 2
    c2.close()
    assert (data / "library.db.sebelum-pulih").exists()
    assert not cadangan.terapkan_bila_ada(data)


def test_cadangan_rusak_ditolak(tmp_path):
    (tmp_path / "library.db").write_bytes(b"bukan database")
    with pytest.raises(ValueError):
        cadangan.periksa(tmp_path)


def test_cadangan_versi_lebih_baru_ditolak(tmp_path):
    c = sqlite3.connect(tmp_path / "library.db")
    c.execute(f"PRAGMA user_version={db.VERSI + 1}")
    c.close()
    with pytest.raises(ValueError):
        cadangan.periksa(tmp_path)


def _token():
    teks = (AKAR / "app/ui/qml/theme/Theme.qml").read_text(encoding="utf-8")
    return {n: (g, t) for n, g, t in re.findall(r'color (\w+): pilih\("(#\w+)", "(#\w+)"\)', teks)}


def _kontras(a, b):
    def lum(h):
        v = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


@pytest.mark.parametrize("tema", [0, 1])
def test_kontras_token_wcag_aa(tema):
    t = _token()
    pasangan = [(a, b) for a in ("teks", "teks2", "teks3") for b in ("kanvas", "permukaan", "sorot")]
    pasangan += [("padaIsi", "isi"), ("padaIsi", "isiSorot"), ("padaIsi", "isiTekan")]
    pasangan += [(a, b) for a in ("teksCangkang", "teksCangkang2") for b in ("cangkang", "cangkangIsi", "cangkangSorot")]
    for a, b in pasangan:
        assert _kontras(t[a][tema], t[b][tema]) >= 4.5, (a, b)


def test_semua_layar_kedua_tema_tanpa_galat_qml(tmp_path):
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    from PySide6.QtTest import QTest

    import main

    galat = []
    lama = qInstallMessageHandler(lambda j, _k, m: galat.append(m) if j != QtMsgType.QtDebugMsg else None)
    try:
        mesin = main.buat_mesin_qml(tmp_path, mulai_wajah=False)
        win = mesin.rootObjects()[0]
        for tema in ("gelap", "terang", "auto"):
            mesin._jembatan[2].aturTema(tema)
            for m in range(6):
                win.setProperty("menuAktif", m)
                QTest.qWait(40)
        assert not [g for g in galat if "qml" in g.lower() or "binding" in g.lower()], galat
    finally:
        qInstallMessageHandler(lama)


def test_jeda_baterai_bisa_dimatikan(tmp_path, monkeypatch):
    from core import daya
    from ui.bridge.galeri import Galeri
    from ui.bridge.pindai import Pindai

    g = Galeri(tmp_path / "a.db", tmp_path / "th")
    p = Pindai(tmp_path / "a.db", tmp_path / "th", g, pekerja=1, jeda_baterai=lambda: False)
    monkeypatch.setattr(daya, "pakai_baterai", lambda: True)
    monkeypatch.setattr(daya, "jaga_terjaga", lambda a: None)
    assert p._harus_jeda() is False


def test_lokasi_data_dari_berkas(tmp_path):
    import main

    assert main.lokasi_data(tmp_path) == tmp_path / "data"
    (tmp_path / "lokasi-data.txt").write_text(str(tmp_path / "lain") + "\n", encoding="utf-8")
    assert main.lokasi_data(tmp_path) == tmp_path / "lain"
