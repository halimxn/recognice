"""Bandingkan ONNX Runtime (yang dipakai sekarang) dengan OpenVINO di CPU dan GPU Intel, untuk model yang sama.

    .venv\\Scripts\\python.exe dev\\bench\\mesin_hitung.py

Memakai thumbnail lokal di data/thumbs (tidak membaca drive foto). Hanya angka agregat yang dicetak.
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
from core import faces  # noqa: E402

M = AKAR / "models/buffalo_l"
ULANG = 12


def waktu(f, n=ULANG):
    f()  # pemanasan
    t = time.perf_counter()
    for _ in range(n):
        f()
    return (time.perf_counter() - t) / n * 1000


def contoh():
    """Kanvas deteksi 640, potongan 192, dan 8 wajah 112 dari thumbnail nyata."""
    berkas = sorted((AKAR / "data/thumbs").rglob("*.1024.jpg"))[:200:10]
    det = faces.Detektor(M / "det_10g.onnx", 4)
    kanvas, wajah = [], []
    for p in berkas:
        g = Image.open(p).convert("RGB")
        k = np.zeros((640, 640, 3), np.float32)
        s = min(640 / g.width, 640 / g.height)
        kecil = g.resize((round(g.width * s), round(g.height * s)))
        k[:kecil.height, :kecil.width] = np.asarray(kecil, np.float32)
        kanvas.append(((k - 127.5) / 128.0).transpose(2, 0, 1)[None].copy())
        for w in det.deteksi(g):
            wajah.append(np.asarray(faces.sejajarkan(g, w.titik), np.float32))
    W = ((np.stack(wajah[:8]) - 127.5) / 127.5).transpose(0, 3, 1, 2).copy()
    return kanvas, W, len(wajah)


def main():
    kanvas, W, n = contoh()
    k640 = kanvas[0]
    k192 = k640[:, :, :192, :192].copy()
    print(f"contoh: {len(kanvas)} kanvas, {n} wajah dari thumbnail lokal")

    hasil = {}
    for benang in (4, 2):
        sd, sr = faces.buat_sesi(M / "det_10g.onnx", benang), faces.buat_sesi(M / "w600k_r50.onnx", benang)
        nd, nr = sd.get_inputs()[0].name, sr.get_inputs()[0].name
        hasil[f"ORT {benang} benang"] = (
            waktu(lambda: sd.run(None, {nd: k640})), waktu(lambda: sd.run(None, {nd: k192})),
            waktu(lambda: sr.run(None, {nr: W[:1]})), waktu(lambda: sr.run(None, {nr: W})) / 8)
        if benang == 4:
            acuan_det = [o for o in sd.run(None, {nd: k640})]
            acuan_emb = sr.run(None, {nr: W})[0]

    for d in ("shiboken6",):
        os.add_dll_directory(str(AKAR / ".venv/Lib/site-packages" / d))
    import openvino as ov

    core = ov.Core()
    core.set_property({"CACHE_DIR": str(AKAR / "data/cache_ov")})
    selisih = {}
    for alat in ("CPU", "GPU"):
        if alat not in core.available_devices:
            continue
        t = time.perf_counter()
        md = core.read_model(str(M / "det_10g.onnx"))
        md.reshape({md.inputs[0]: [1, 3, 640, 640]})
        d640 = core.compile_model(md, alat, {"PERFORMANCE_HINT": "LATENCY"})
        md = core.read_model(str(M / "det_10g.onnx"))
        md.reshape({md.inputs[0]: [1, 3, 192, 192]})
        d192 = core.compile_model(md, alat, {"PERFORMANCE_HINT": "LATENCY"})
        r1, r8 = [], []
        for b, simpan in ((1, r1), (8, r8)):
            mr = core.read_model(str(M / "w600k_r50.onnx"))
            mr.reshape({mr.inputs[0]: [b, 3, 112, 112]})
            simpan.append(core.compile_model(mr, alat, {"PERFORMANCE_HINT": "LATENCY"}))
        siap = time.perf_counter() - t
        hasil[f"OpenVINO {alat}"] = (waktu(lambda: d640(k640)), waktu(lambda: d192(k192)), waktu(lambda: r1[0](W[:1])), waktu(lambda: r8[0](W)) / 8)
        keluar = d640(k640)
        beda_det = max(float(np.abs(np.asarray(keluar[i]) - acuan_det[i]).max()) for i in range(len(acuan_det)))
        e = r8[0](W)[0]
        e = e / np.linalg.norm(e, axis=1, keepdims=True)
        a = acuan_emb / np.linalg.norm(acuan_emb, axis=1, keepdims=True)
        selisih[alat] = (beda_det, float((e * a).sum(1).min()), siap)

    print(f"{'':20s} {'deteksi 640':>12s} {'deteksi 192':>12s} {'1 wajah':>10s} {'per wajah (8)':>14s}   (milidetik)")
    for k, (a, b, c, d) in hasil.items():
        print(f"{k:20s} {a:12.0f} {b:12.1f} {c:10.0f} {d:14.0f}")
    for alat, (bd, cos, siap) in selisih.items():
        print(f"OpenVINO {alat}: selisih keluaran deteksi maks {bd:.4f}, kemiripan embedding dengan ORT min {cos:.5f}, siap dalam {siap:.1f} dtk")


if __name__ == "__main__":
    main()
