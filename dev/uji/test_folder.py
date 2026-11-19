import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from core import db, library  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def jalur(tmp_path):
    p = tmp_path / "library.db"
    c = db.buka(p)
    c.execute("INSERT INTO source(id, serial, akar_relatif, huruf_terakhir, label) VALUES (1,'','x','C:','Foto')")
    data = [("2020/Liburan/a.jpg", 5), ("2020/Liburan/b.jpg", 9), ("2020/c.jpg", 1), ("2021/d.jpg", 3), ("e.jpg", 2)]
    for i, (rel, t) in enumerate(data):
        c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (1,?,1,1,?,4,3,?,'ok')",
                  (rel, f"{i:040x}", t))
    c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, status) VALUES (1,'2022/h.jpg',1,1,'ff',4,3,99,'hilang')")
    c.commit()
    c.close()
    return p


def test_anak_folder_terhitung_dengan_subfolder_dan_sampul_terbaru(jalur):
    c = db.buka(jalur)
    p = library.pohon_folder(c)
    akar = p[1, ""]
    assert akar["jumlah"] == 5 and sorted(akar["anak"]) == ["2020", "2021"]
    t = p[1, "2020"]
    assert t["jumlah"] == 3 and t["sha1"] == f"{1:040x}" and t["anak"] == {"2020/Liburan"} or t["anak"] == ["2020/Liburan"]


def test_folder_hanya_foto_ok(jalur):
    c = db.buka(jalur)
    assert (1, "2022") not in library.pohon_folder(c)


def _folder(jalur):
    from ui.bridge.folder import Folder

    return Folder(jalur, jalur.parent / "th")


def test_folder_tertunda_baru_membaca_saat_disegarkan(jalur):
    from ui.bridge.folder import Folder

    f = Folder(jalur, jalur.parent / "th", muat=False)
    assert f.anak == [] and f.jumlah == 0 and f.dinding == []
    f.segarkan()
    assert [a["nama"] for a in f.anak] == ["2020", "2021"]


def test_satu_sumber_langsung_menampilkan_isinya(jalur):
    f = _folder(jalur)
    assert [a["nama"] for a in f.anak] == ["2020", "2021"]
    assert f.anak[0]["jumlah"] == 3 and f.anak[0]["url"].endswith(f"{1:040x}.256.jpg")
    assert f.dalam is False


def test_masuk_dan_naik(jalur):
    f = _folder(jalur)
    f.masuk(1, "2020")
    assert [a["nama"] for a in f.anak] == ["Liburan"] and f.dalam and f.judul == "2020"
    assert f.anak[0]["punyaAnak"] is False
    f.naik()
    assert f.dalam is False


def test_jejak_folder_dan_kembali_ke_akar(jalur):
    f = _folder(jalur)
    assert f.jejak == []
    f.masuk(1, "2020/Liburan")
    assert [(j["nama"], j["rel"]) for j in f.jejak] == [("2020", "2020"), ("Liburan", "2020/Liburan")]
    f.keAkar()
    assert f.dalam is False


def test_saringan_folder_saat_ini(jalur):
    f = _folder(jalur)
    f.masuk(1, "2020")
    assert f.saringanIni() == {"folder": {"source": 1, "rel": "2020"}, "label": "2020"}


def test_folder_yang_hilang_kembali_ke_akar(jalur):
    f = _folder(jalur)
    f.masuk(1, "2020")
    c = db.buka(jalur)
    c.execute("UPDATE photo SET status='hilang' WHERE rel LIKE '2020/%'")
    c.commit()
    f.segarkan()
    assert f.dalam is False and [a["nama"] for a in f.anak] == ["2021"]


def test_galeri_tertunda_tidak_memuat_semua(jalur):
    from ui.bridge.galeri import Galeri

    g = Galeri(jalur, jalur.parent / "th", muat_awal=False)
    assert g.jumlah == 0
    g.muatUlang()
    assert g.jumlah == 0
    g.saring({"folder": {"source": 1, "rel": "2020"}, "label": "2020"})
    assert g.jumlah == 3
    g.hapusSaring()
    assert g.jumlah == 0
    g.pastikanMuat()
    assert g.jumlah == 5


def test_sampul_tiga_foto_terbaru_tiap_folder(jalur):
    p = library.pohon_folder(db.buka(jalur))
    assert p[1, "2020"]["sampul"] == [f"{1:040x}", f"{0:040x}", f"{2:040x}"]
    assert p[1, "2021"]["sampul"] == [f"{3:040x}"]


def test_kartu_folder_membawa_kolase_dan_jumlah_subfolder(jalur):
    a = _folder(jalur).anak[0]
    assert len(a["urls"]) == 3 and a["urls"][0] == a["url"] and a["subfolder"] == 1


def test_foto_terbaru_dibatasi_dan_mengikuti_folder(jalur):
    c = db.buka(jalur)
    assert [f.taken_at for f in library.foto_terbaru(c, None, 2)] == [9, 5]
    assert [f.taken_at for f in library.foto_terbaru(c, {"folder": {"source": 1, "rel": "2021"}}, 9)] == [3]


def test_dinding_foto_akar_terbaru_dulu(jalur):
    f = _folder(jalur)
    f.atur(5000)
    assert len(f.dinding) == 5 and f.tinggiDinding > 0 and f.judulDinding == "Foto terbaru"
    assert f.dinding[0]["url"].endswith(f"{1:040x}.256.jpg")
    assert set(f.dinding[0]) >= {"x", "y", "w", "h", "url", "id"}
    assert f.saringanDinding() == {"foto": [d["id"] for d in f.dinding], "label": "Foto terbaru"}


def test_dinding_tidak_berakhir_dengan_baris_setengah(jalur):
    f = _folder(jalur)
    f.atur(420)
    baris = {}
    for d in f.dinding:
        baris.setdefault(d["y"], []).append(d)
    assert len(baris) >= 1
    for isi in baris.values():
        assert max(d["x"] + d["w"] for d in isi) == 420


def test_dinding_mengikuti_folder_yang_dibuka(jalur):
    f = _folder(jalur)
    f.atur(5000)
    f.masuk(1, "2020")
    assert len(f.dinding) == 3 and f.judulDinding == "Foto di folder ini"
    f.naik()
    assert len(f.dinding) == 5
