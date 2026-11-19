"""Membandingkan model embedding pada set emas: dev/eval/gold/<nama orang>/*.jpg

Tiap foto dianggap memuat orang itu sebagai wajah terbesar. Aturan keputusan: rancangan §14.
"""
import itertools
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from core.faces import Detektor, Pengenal, sejajarkan  # noqa: E402

M = AKAR / "models"
GOLD = AKAR / "dev/eval/gold"
PENGENAL = {"mbf": M / "lama/rec.onnx", "r50": M / "buffalo_l/w600k_r50.onnx", "r100": M / "antelopev2/glintr100.onnx"}
AMBANG_NAIK = 0.015  # R100 harus menang >= 1,5 poin TAR untuk layak dua kali biaya CPU


def tar_pada_far(positif, negatif, far):
    # shortcut: FAR tidak bisa lebih kecil dari 1/len(negatif); set besar diperlukan untuk 1e-4
    batas = np.quantile(negatif, 1 - far)
    return float((positif > batas).mean()), float(batas)


def muat_potongan():
    det = Detektor(M / "buffalo_l/det_10g.onnx", 4)
    potongan, label, lewat = [], [], 0
    for orang in sorted(p for p in GOLD.iterdir() if p.is_dir()):
        for f in sorted(orang.iterdir()):
            try:
                im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
            except Exception:
                lewat += 1
                continue
            im.thumbnail((1280, 1280), Image.Resampling.BILINEAR)
            wajah = det.deteksi(im, sisi=1280)
            if not wajah:
                lewat += 1
                continue
            besar = max(wajah, key=lambda w: (w.kotak[2] - w.kotak[0]) * (w.kotak[3] - w.kotak[1]))
            potongan.append(sejajarkan(im, besar.titik))
            label.append(orang.name)
    return potongan, np.array(label), lewat


def main():
    if not GOLD.is_dir() or not any(GOLD.iterdir()):
        sys.exit(f"Set emas belum ada: taruh foto di {GOLD}\\<nama orang>\\")
    potongan, label, lewat = muat_potongan()
    print(f"{len(potongan)} wajah, {len(set(label))} orang, {lewat} foto dilewati")
    hasil = {}
    for nama, jalur in PENGENAL.items():
        pg = Pengenal(jalur, 4)
        v = np.vstack([pg.embed([w]) for w in potongan])
        kem = v @ v.T
        pos, neg = [], []
        for i, j in itertools.combinations(range(len(v)), 2):
            (pos if label[i] == label[j] else neg).append(kem[i, j])
        pos, neg = np.array(pos), np.array(neg)
        tar3, b3 = tar_pada_far(pos, neg, 1e-3)
        tar2, b2 = tar_pada_far(pos, neg, 1e-2)
        hasil[nama] = tar3
        print(f"{nama:5} TAR@FAR1e-3 {tar3:.4f} (ambang {b3:.3f})  TAR@FAR1e-2 {tar2:.4f} (ambang {b2:.3f})  "
              f"pasangan +{len(pos)} / -{len(neg)}")
    selisih = hasil["r100"] - hasil["r50"]
    print(f"selisih r100-r50 = {selisih:+.4f}; aturan §14 memilih {'r100' if selisih >= AMBANG_NAIK else 'r50'}")
    if len(neg) < 1000:
        print("peringatan: pasangan negatif < 1000, TAR@FAR1e-3 tidak bermakna")


if __name__ == "__main__":
    main()
