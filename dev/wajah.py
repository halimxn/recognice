"""Tahap wajah dari baris perintah: dev/wajah.py [jumlah foto]. Mencetak agregat saja."""
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR / "app"))

from core import daya, db, pipa_wajah  # noqa: E402

if __name__ == "__main__":
    c = db.buka(AKAR / "data/library.db")
    batas = int(sys.argv[1]) if len(sys.argv) > 1 else None
    m = AKAR / "models/buffalo_l"
    t0 = time.perf_counter()
    awal = [None]

    def lapor(a, b):
        if awal[0] is None:
            awal[0] = (time.perf_counter(), a)
        print(f"{a}/{b} {time.perf_counter() - t0:.0f}s", flush=True)

    daya.jaga_terjaga(True)
    r = pipa_wajah.PemindaiWajah(c, AKAR / "data/thumbs", model=(str(m / "det_10g.onnx"), str(m / "w600k_r50.onnx"), 4)).jalankan(
        jeda=daya.pakai_baterai, lapor=lapor, batas=batas)
    daya.jaga_terjaga(False)
    print("SELESAI", r, f"{time.perf_counter() - t0:.0f}s", flush=True)
