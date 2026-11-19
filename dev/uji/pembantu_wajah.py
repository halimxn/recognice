"""Pengganti olah/muat untuk proses pekerja di uji (harus bisa diimpor oleh proses anak)."""
import os

import numpy as np

from core import pipa_wajah


def muat_palsu():
    pass


def _wajah(n):
    v = np.zeros(512, np.float16)
    v[0] = 1
    return [(0.1, 0.1, 0.3, 0.3, b"\0" * 40, 0.9, 120.0, 300.0, 0.9, 0.8, v.tobytes()) for _ in range(n)]


def olah_palsu(tugas):
    pratinjau, asli = tugas[:2]
    nama = os.path.basename(pratinjau)
    if nama.startswith("ab"):
        tanda = pratinjau + ".sudah"
        if not os.path.exists(tanda):
            os.makedirs(os.path.dirname(tanda), exist_ok=True)
            open(tanda, "w").close()
            os._exit(1)
        return _wajah(1)
    if nama.startswith("aa"):
        return _wajah(2)
    if nama.startswith("bb"):
        return []
    if nama.startswith("cc"):
        if asli is None:
            raise pipa_wajah.PerluAsli()
        return _wajah(1)
    if nama.startswith("dd"):
        os._exit(1)
    if nama.startswith("ee"):
        raise pipa_wajah.GagalWajah("rusak")
    return _wajah(1)


def buka_asli(jalur):
    """Dijalankan di pekerja yang dimuat `pipa_wajah.muat`: membuktikan format didaftarkan di sana."""
    st = os.stat(jalur)
    return pipa_wajah._pengambil(jalur, st.st_size, st.st_mtime_ns)(64).size
