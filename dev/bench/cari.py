"""Kecepatan pencarian pada pustaka nyata. Hanya mencetak waktu dan jumlah."""
import statistics as st
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

import numpy as np  # noqa: E402

from core import cari, db, library  # noqa: E402

c = db.buka(AKAR / "data/library.db")
t = time.perf_counter()
i = cari.Indeks(c)
i._segarkan()
print(f"bangun indeks: {(time.perf_counter() - t) * 1000:.0f} ms, {len(i._ids)} wajah")
if len(i._ids):
    pilih = np.random.default_rng(1).choice(len(i._ids), min(50, len(i._ids)), replace=False)
    w = []
    for k in pilih:
        a = time.perf_counter()
        i.cari(i._V[k], kecuali=int(i._ids[k]))
        w.append((time.perf_counter() - a) * 1000)
    print(f"cari wajah: median {st.median(w):.1f} ms, maks {max(w):.1f} ms, n={len(w)}")

V = np.random.default_rng(2).standard_normal((45000, 512), np.float32)
V /= np.linalg.norm(V, axis=1, keepdims=True)
i2 = cari.Indeks(c)
i2._muat_matriks(np.arange(45000), V)
w = []
for k in range(30):
    a = time.perf_counter()
    i2._peringkat(V[k], None)
    w.append((time.perf_counter() - a) * 1000)
print(f"peringkat 45.000 wajah sintetis: median {st.median(w):.1f} ms, maks {max(w):.1f} ms")

w = []
for teks in ("a", "foto", "2021", "maret 2021", "wisuda"):
    a = time.perf_counter()
    cari.saran_teks(c, teks)
    w.append((time.perf_counter() - a) * 1000)
print(f"saran teks: median {st.median(w):.1f} ms, maks {max(w):.1f} ms")
a = time.perf_counter()
library.hitung(c, {"tahun": 2021})
print(f"hitung saringan: {(time.perf_counter() - a) * 1000:.1f} ms")
