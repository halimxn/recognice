"""Pengganti proses contoh untuk uji (harus bisa diimpor oleh proses anak)."""
import numpy as np


def muat_palsu(*_):
    pass


def _v(i):
    v = np.zeros(512, np.float16)
    v[i] = 1
    return v.tobytes()


def contoh_palsu(jalur, akar):
    if jalur.endswith("rusak.jpg"):
        raise ValueError("tidak terbaca")
    if jalur.endswith("kosong.jpg"):
        return "ab" * 20, []
    if jalur.endswith("dua.jpg"):
        return "ab" * 20, [(0.1, 0.1, 0.3, 0.3, _v(0)), (0.5, 0.1, 0.7, 0.3, _v(1))]
    return "ab" * 20, [(0.1, 0.1, 0.3, 0.3, _v(0))]
