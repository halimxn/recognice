import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core.layout import baris_di_y, susun


def foto(rasio, hari):
    return (rasio, hari)


def test_lebar_baris_pas():
    t = susun([foto(1.5, "a")] * 30, lebar=1000, tinggi=200, jarak=4, kepala=40)
    penuh = [b for b in t.baris if b.jenis == "foto"][:-1]
    assert penuh
    for b in penuh:
        ujung = b.isi[-1]
        assert abs(ujung.x + ujung.w - 1000) <= 1


def test_kepala_per_hari():
    t = susun([foto(1, "a"), foto(1, "a"), foto(1, "b")], 1000, 200, 4, 40)
    assert [b.label for b in t.baris if b.jenis == "kepala"] == ["a", "b"]


def test_baris_terakhir_hari_tidak_meregang():
    t = susun([foto(1, "a")], 1000, 200, 4, 40)
    b = [x for x in t.baris if x.jenis == "foto"][0]
    assert b.isi[0].w == 200


def test_y_berurutan():
    t = susun([foto(1.3, str(i // 7)) for i in range(100)], 1000, 200, 4, 40)
    y = 0
    for b in t.baris:
        assert b.y == y
        y += b.tinggi
    assert t.tinggi_total == y


def test_baris_di_y():
    t = susun([foto(1.3, "a")] * 100, 1000, 200, 4, 40)
    b = t.baris[5]
    assert baris_di_y(t, b.y + 1) == 5
    assert baris_di_y(t, -50) == 0
    assert baris_di_y(t, t.tinggi_total + 500) == len(t.baris) - 1


def test_indeks_foto_berurutan():
    t = susun([foto(1.3, str(i // 4)) for i in range(50)], 1000, 200, 4, 40)
    assert [i.indeks for b in t.baris for i in b.isi] == list(range(50))


def test_panorama_ekstrem_tetap_di_lebar():
    t = susun([foto(20, "a")], 1000, 200, 4, 40)
    b = [x for x in t.baris if x.jenis == "foto"][0]
    assert b.isi[0].w <= 1000
