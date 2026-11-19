import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core.faces import TEMPLAT_112, nms, sejajarkan, similaritas, urai_scrfd


def test_similaritas_memulihkan_transformasi():
    sudut = np.deg2rad(25)
    r = 1.7 * np.array([[np.cos(sudut), -np.sin(sudut)], [np.sin(sudut), np.cos(sudut)]])
    asal = TEMPLAT_112.astype(np.float64)
    tujuan = asal @ r.T + [30, -12]
    m = similaritas(asal, tujuan)
    assert np.allclose(m[:, :2], r, atol=1e-6)
    assert np.allclose(m[:, 2], [30, -12], atol=1e-6)


def test_sejajarkan_menaruh_titik_di_templat():
    g = Image.new("RGB", (400, 400))
    titik = TEMPLAT_112 * 2 + [50, 70]
    ptk = g.load()
    x, y = map(int, titik[2])
    for i in range(-3, 4):
        for j in range(-3, 4):
            ptk[x + i, y + j] = (255, 255, 255)
    h = np.asarray(sejajarkan(g, titik)).sum(2)
    py, px = np.unravel_index(h.argmax(), h.shape)
    assert abs(px - TEMPLAT_112[2, 0]) <= 2 and abs(py - TEMPLAT_112[2, 1]) <= 2


def test_urai_scrfd_koordinat():
    sisi = 64
    keluaran = []
    for stride in (8, 16, 32):
        n = (sisi // stride) ** 2 * 2
        keluaran.append(np.zeros((1, n, 1), np.float32))
    for stride in (8, 16, 32):
        n = (sisi // stride) ** 2 * 2
        keluaran.append(np.ones((1, n, 4), np.float32))
    for stride in (8, 16, 32):
        n = (sisi // stride) ** 2 * 2
        keluaran.append(np.zeros((1, n, 10), np.float32))
    # stride 16 (indeks 1), sel baris 1 kolom 2, anchor kedua: pusat (40, 24), jarak 16
    keluaran[1][0, (1 * 4 + 2) * 2 + 1, 0] = 0.9
    skor, kotak, titik = urai_scrfd(keluaran, sisi, sisi, 0.5)
    assert skor.tolist() == [np.float32(0.9)]
    assert np.allclose(kotak[0], [24, 8, 56, 40])
    assert np.allclose(titik[0], [[40, 24]] * 5)


def test_nms_membuang_tumpang_tindih():
    kotak = np.array([[0, 0, 10, 10], [1, 1, 10, 10], [50, 50, 60, 60]], np.float32)
    assert nms(kotak, np.array([0.9, 0.8, 0.7])) == [0, 2]
