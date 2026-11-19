"""Kecepatan detektor dan embedding di CPU ini, pada contoh foto nyata. Keluaran hanya agregat."""
import json
import os
import random
import statistics as st
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))

from PIL import Image, ImageOps  # noqa: E402

from core.faces import Detektor, Pengenal, sejajarkan  # noqa: E402

M = AKAR / "models"
DETEKTOR = {"2.5G": M / "lama/det.onnx", "10G": M / "buffalo_l/det_10g.onnx"}
PENGENAL = {"mbf": M / "lama/rec.onnx", "r50": M / "buffalo_l/w600k_r50.onnx", "r100": M / "antelopev2/glintr100.onnx"}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def muat_contoh():
    semua = [p for p, _ in json.loads((Path(__file__).parent / "out/jalur.json").read_text(encoding="utf-8"))
             if p.lower().endswith((".jpg", ".jpeg"))]
    random.Random(7).shuffle(semua)
    hasil = []
    for p in semua:
        if len(hasil) == N:
            break
        try:
            im = Image.open(p)
            im.draft("RGB", (1280, 1280))
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((1280, 1280), Image.Resampling.BILINEAR)
            hasil.append(im)
        except Exception:
            continue
    return hasil


def main():
    contoh = muat_contoh()
    print(f"contoh: {len(contoh)} foto, {os.cpu_count()} thread logis")
    wajah_acuan = []
    for nama, jalur in DETEKTOR.items():
        for sisi in (640, 1280):
            for benang in (2, 4):
                det = Detektor(jalur, benang)
                wkt, jml = [], 0
                try:
                    for im in contoh:
                        a = time.perf_counter()
                        hasil = det.deteksi(im, sisi=sisi)
                        wkt.append(time.perf_counter() - a)
                        jml += len(hasil)
                        if nama == "10G" and sisi == 1280 and benang == 4:
                            wajah_acuan += [(im, w) for w in hasil]
                except Exception as e:
                    print(f"det {nama} @{sisi}: gagal: {str(e)[:80]}")
                    break
                print(f"det {nama:5} @{sisi:4} {benang} benang: median {st.median(wkt) * 1000:7.0f} ms/foto, "
                      f"rata2 {st.mean(wkt) * 1000:7.0f}, wajah {jml}")

    potongan = [sejajarkan(im, w.titik) for im, w in wajah_acuan[:60]]
    print(f"wajah acuan: {len(wajah_acuan)}; rata2 {len(wajah_acuan) / max(len(contoh), 1):.2f} per foto")
    if not potongan:
        return
    for nama, jalur in PENGENAL.items():
        print(f"{nama}: {jalur.stat().st_size / 1e6:.0f} MB")
        for benang in (1, 2, 4):
            pg = Pengenal(jalur, benang)
            wkt = []
            for w in potongan:
                a = time.perf_counter()
                pg.embed([w])
                wkt.append(time.perf_counter() - a)
            print(f"  {benang} benang: median {st.median(wkt) * 1000:6.0f} ms/wajah")


if __name__ == "__main__":
    main()
