"""Ukur daya pisah embedding pada pustaka sendiri, tanpa label dan tanpa set emas.

    .venv\\Scripts\\python.exe dev\\eval\\tanpa_label.py [jalur library.db]

Beda orang : dua wajah dalam satu foto (hampir pasti orang berbeda; kolase dan cermin adalah pengecualian).
Sama orang : wajah di posisi yang sama pada dua foto beruntun (selang <= 5 detik, ukuran foto sama).
Pasangan "sama orang" ini mudah (pose dan cahaya nyaris sama), jadi angkanya batas atas, bukan akurasi.
Database dibuka baca-saja dan hanya angka agregat yang dicetak.
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
from core import kelompok  # noqa: E402
from core.pipa_wajah import MODEL  # noqa: E402

SELANG_BERUNTUN = 5


def muat(jalur, model=MODEL):
    c = sqlite3.connect(f"file:{Path(jalur).as_posix()}?mode=ro", uri=True)
    b = c.execute(
        "SELECT f.photo_id, f.x1, f.y1, f.x2, f.y2, f.lebar_px, f.skor, f.tajam, f.frontal, f.embedding, p.taken_at, p.lebar, p.tinggi "
        "FROM face f JOIN photo p ON p.id=f.photo_id WHERE f.model=? ORDER BY p.taken_at, f.photo_id", (model,)).fetchall()
    c.close()
    if not b:
        return None
    V = np.frombuffer(b"".join(x[9] for x in b), np.float16).reshape(-1, 512).astype(np.float32)
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
    kol = lambda k: np.array([x[k] for x in b], np.float32)  # noqa: E731
    layak = (kol(5) >= kelompok.MIN_LEBAR) & (kol(6) >= kelompok.MIN_SKOR) & (kol(7) >= kelompok.MIN_TAJAM) & (kol(8) >= kelompok.MIN_FRONTAL)
    return {"V": V, "foto": np.array([x[0] for x in b]), "kotak": np.array([x[1:5] for x in b], np.float32), "layak": layak,
            "waktu": np.array([x[10] for x in b]), "ukuran": [(x[11], x[12]) for x in b]}


def sama_beruntun(d):
    """Kemiripan wajah yang posisinya sama di dua foto beruntun."""
    foto, V, kotak = d["foto"], d["V"], d["kotak"]
    urut, awal = np.unique(foto, return_index=True)
    awal = np.sort(awal)
    grup = np.split(np.arange(len(foto)), awal[1:])
    hasil = []
    for a, b in zip(grup, grup[1:]):
        if not (0 < d["waktu"][b[0]] - d["waktu"][a[0]] <= SELANG_BERUNTUN) or d["ukuran"][a[0]] != d["ukuran"][b[0]]:
            continue
        ca, cb = (kotak[a, :2] + kotak[a, 2:]) / 2, (kotak[b, :2] + kotak[b, 2:]) / 2
        D = np.linalg.norm(ca[:, None] - cb[None], axis=2)
        for i in range(len(a)):
            j = int(D[i].argmin())
            if D[i, j] < 0.5 * (kotak[a[i], 2] - kotak[a[i], 0]) and int(D[:, j].argmin()) == i:
                hasil.append(float(V[a[i]] @ V[b[j]]))
    return np.array(hasil, np.float32)


def lapor(nama, d):
    beda = kelompok.kemiripan_satu_foto(d["V"], d["foto"], d["layak"])
    sama = sama_beruntun(d)
    print(f"{nama}: {len(d['V'])} wajah ({d['layak'].mean():.0%} layak), {len(np.unique(d['foto']))} foto")
    if len(beda) < 50:
        print("  terlalu sedikit pasangan satu foto untuk diukur")
        return
    q = np.percentile(beda, [50, 90, 99, 99.9])
    print(f"  beda orang n={len(beda)}: median {q[0]:.3f}  p90 {q[1]:.3f}  p99 {q[2]:.3f}  p99,9 {q[3]:.3f}")
    for a in (0.45, 0.50, 0.55, 0.60):
        print(f"    di atas {a:.2f}: {100 * (beda >= a).mean():5.2f} %")
    print(f"  ambang tepi dari data ini: {kelompok.ambang_dari_data(beda):.3f}")
    if len(sama) >= 10:
        dp = (sama.mean() - beda.mean()) / np.sqrt((sama.var() + beda.var()) / 2)
        print(f"  sama orang (beruntun) n={len(sama)}: p10 {np.percentile(sama, 10):.3f}  median {np.median(sama):.3f} | "
              f"di atas p99 beda-orang: {100 * (sama > q[2]).mean():.0f} % | d' = {dp:.2f}")
    else:
        print(f"  sama orang (beruntun): hanya {len(sama)} pasangan, tidak cukup")


if __name__ == "__main__":
    jalur = sys.argv[1] if len(sys.argv) > 1 else AKAR / "data" / "library.db"
    c = sqlite3.connect(f"file:{Path(jalur).as_posix()}?mode=ro", uri=True)
    model = [m for (m,) in c.execute("SELECT DISTINCT model FROM face")]
    c.close()
    for m in model:
        d = muat(jalur, m)
        if d:
            lapor(m, d)
