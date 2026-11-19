"""Cek numerik pipa deteksi-sejajar-embed: wajah sama pada skala berbeda harus mirip, wajah lain tidak. Hanya agregat."""
import json
import random
import statistics as st
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from core.faces import Detektor, Pengenal, sejajarkan  # noqa: E402

M = AKAR / "models"
semua = [p for p, _ in json.loads((Path(__file__).parent / "out/jalur.json").read_text(encoding="utf-8"))
         if p.lower().endswith((".jpg", ".jpeg"))]
random.Random(7).shuffle(semua)
det = Detektor(M / "buffalo_l/det_10g.onnx", 4)
luas = lambda w: (w.kotak[2] - w.kotak[0]) * (w.kotak[3] - w.kotak[1])
pasang = []
for p in semua[:120]:
    if len(pasang) == 24:
        break
    try:
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    except Exception:
        continue
    im.thumbnail((1280, 1280), Image.Resampling.BILINEAR)
    kecil = im.resize((int(im.width * 0.7), int(im.height * 0.7)), Image.Resampling.BILINEAR)
    a, b = det.deteksi(im), det.deteksi(kecil)
    if a and b and min(max(map(luas, a)), max(map(luas, b))) > 80 ** 2:
        pasang.append((sejajarkan(im, max(a, key=luas).titik), sejajarkan(kecil, max(b, key=luas).titik)))
print(f"pasangan wajah: {len(pasang)}")
for nama, jalur in {"mbf": "lama/rec.onnx", "r50": "buffalo_l/w600k_r50.onnx", "r100": "antelopev2/glintr100.onnx"}.items():
    pg = Pengenal(M / jalur, 4)
    v1 = np.vstack([pg.embed([a]) for a, _ in pasang])
    v2 = np.vstack([pg.embed([b]) for _, b in pasang])
    k = v1 @ v2.T
    sama = np.diag(k)
    lain = k[~np.eye(len(k), dtype=bool)]
    print(f"{nama:5} sama: median {st.median(sama):.3f}, min {sama.min():.3f}   lain: median {st.median(lain):.3f}, p99 {np.percentile(lain, 99):.3f}")
