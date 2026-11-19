"""Pindai sumber dari baris perintah: dev/pindai.py <folder>."""
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR / "app"))

from core import daya, db, library, scanner  # noqa: E402

if __name__ == "__main__":
    c = db.buka(AKAR / "data/library.db")
    sid = library.tambah_sumber(c, sys.argv[1])
    t0 = time.perf_counter()
    daya.jaga_terjaga(True)

    def lapor(a, b):
        print(f"{a}/{b} {time.perf_counter() - t0:.0f}s", flush=True)

    r = scanner.Pemindai(c, AKAR / "data/thumbs").jalankan(sid, jeda=daya.pakai_baterai, lapor=lapor)
    daya.jaga_terjaga(False)
    print("SELESAI", r, f"{time.perf_counter() - t0:.0f}s", flush=True)
