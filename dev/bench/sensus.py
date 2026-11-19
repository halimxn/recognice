"""Sensus format pustaka: hanya nama dan ukuran file, isi tidak dibuka. Hanya mencetak agregat."""
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

AKAR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:\01 Foto dan Video")
KELUAR = Path(__file__).parent / "out"


def main():
    KELUAR.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    jenis = defaultdict(lambda: [0, 0])
    jalur = []
    tumpuk = [str(AKAR)]
    while tumpuk:
        with os.scandir(tumpuk.pop()) as it:
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    tumpuk.append(e.path)
                elif e.is_file(follow_symlinks=False):
                    ext = os.path.splitext(e.name)[1].lower()
                    uk = e.stat().st_size
                    jenis[ext][0] += 1
                    jenis[ext][1] += uk
                    jalur.append((e.path, uk))
    (KELUAR / "jalur.json").write_text(json.dumps(jalur), encoding="utf-8")
    print(f"pemindaian: {time.perf_counter() - t0:.1f} s, {len(jalur)} file")
    for ext, (n, uk) in sorted(jenis.items(), key=lambda x: -x[1][0])[:20]:
        print(f"{ext or '(tanpa)':10} {n:7d} {uk / 1e9:8.1f} GB  rata2 {uk / max(n, 1) / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
