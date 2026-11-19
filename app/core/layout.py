"""Tata letak baris rata. Fungsi murni: tinggi total tepat, sehingga scrubber akurat."""
from bisect import bisect_right
from dataclasses import dataclass

RASIO_MIN = 0.5
RASIO_MAKS = 3.0  # panorama dipotong tengah agar baris tetap terbaca


@dataclass(slots=True)
class Sel:
    indeks: int
    x: int
    w: int


@dataclass(slots=True)
class Baris:
    y: int
    tinggi: int
    jenis: str  # "kepala" atau "foto"
    label: str
    isi: list


@dataclass(slots=True)
class Tata:
    baris: list
    ys: list
    tinggi_total: int
    lebar: int


def _sel(awal, rasio, tinggi_foto, lebar_ruang, jarak, rata):
    k = (lebar_ruang - jarak * (len(rasio) - 1)) / (sum(rasio) * tinggi_foto) if rata else 1.0
    h = round(tinggi_foto * k)
    isi, x = [], 0.0
    for i, r in enumerate(rasio):
        w = r * tinggi_foto * k
        isi.append(Sel(awal + i, round(x), round(w)))
        x += w + jarak
    if rata:
        isi[-1].w = lebar_ruang - isi[-1].x
    return isi, h


def susun(foto, lebar, tinggi, jarak, kepala):
    """`foto` berisi (rasio, label hari) urut tampil. Baris terakhir tiap hari tidak diregangkan."""
    baris, y = [], 0

    def tutup(awal, rasio, rata):
        nonlocal y
        isi, h = _sel(awal, rasio, tinggi, lebar, jarak, rata)
        baris.append(Baris(y, h + jarak, "foto", "", isi))
        y += h + jarak

    hari, awal, rasio, lebar_kini = None, 0, [], 0.0
    for i, (r, label) in enumerate(foto):
        r = min(max(r, RASIO_MIN), RASIO_MAKS)
        if label != hari:
            if rasio:
                tutup(awal, rasio, False)
            baris.append(Baris(y, kepala, "kepala", label, []))
            y += kepala
            hari, awal, rasio, lebar_kini = label, i, [], 0.0
        tambah = r * tinggi + (jarak if rasio else 0)
        if rasio and abs(lebar - lebar_kini) < abs(lebar_kini + tambah - lebar):
            tutup(awal, rasio, True)
            awal, rasio, lebar_kini = i, [], 0.0
            tambah = r * tinggi
        rasio.append(r)
        lebar_kini += tambah
        if lebar_kini >= lebar:
            tutup(awal, rasio, True)
            awal, rasio, lebar_kini = i + 1, [], 0.0
    if rasio:
        tutup(awal, rasio, False)
    return Tata(baris, [b.y for b in baris], y, lebar)


def baris_di_y(tata, y):
    return max(0, min(bisect_right(tata.ys, y) - 1, len(tata.baris) - 1))
