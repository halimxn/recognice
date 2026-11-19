"""Mengukur biaya tahap A: baca HDD, SHA-1, dekode, thumbnail. Hanya membaca foto; keluaran hanya agregat."""
import hashlib
import io
import json
import random
import statistics as st
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

KELUAR = Path(__file__).parent / "out"
EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def baca(daftar):
    hasil = []
    t0 = time.perf_counter()
    for p in daftar:
        try:
            with open(p, "rb") as f:
                hasil.append((p, f.read()))
        except OSError:
            pass
    return hasil, time.perf_counter() - t0


def dekode(data, draft):
    im = Image.open(io.BytesIO(data))
    if draft:
        im.draft("RGB", (1280, 1280))
    im = ImageOps.exif_transpose(im).convert("RGB")
    return im


def tahap_a(data):
    t = {}
    a = time.perf_counter()
    hashlib.sha1(data).digest()
    t["sha1"] = time.perf_counter() - a
    a = time.perf_counter()
    im = dekode(data, True)
    t["dekode_draft"] = time.perf_counter() - a
    a = time.perf_counter()
    b = im.copy()
    b.thumbnail((1024, 1024), Image.Resampling.BILINEAR, reducing_gap=2.0)
    b.save(io.BytesIO(), "JPEG", quality=82)
    c = b.copy()
    c.thumbnail((256, 256), Image.Resampling.BILINEAR, reducing_gap=2.0)
    c.save(io.BytesIO(), "JPEG", quality=78)
    t["thumbnail"] = time.perf_counter() - a
    return t


def main():
    semua = [(p, u) for p, u in json.loads((KELUAR / "jalur.json").read_text(encoding="utf-8"))
             if Path(p).suffix.lower() in EXT]
    random.Random(1911).shuffle(semua)
    urut = sorted(p for p, _ in semua[:N])
    acak = [p for p, _ in semua[N:2 * N]]  # set terpisah: set yang sama akan terbaca dari cache Windows

    isi, dt_urut = baca(urut)
    isi2, dt_acak = baca(acak)
    mb = sum(len(d) for _, d in isi) / 1e6
    print(f"baca urut jalur: {dt_urut / len(isi):.3f} s/foto ({mb / dt_urut:.1f} MB/s, n={len(isi)})")
    print(f"baca acak      : {dt_acak / len(isi2):.3f} s/foto (n={len(isi2)})")

    per_ext, per_tahap, gagal, banding = {}, {}, 0, []
    for p, d in isi:
        try:
            t = tahap_a(d)
        except Exception:
            gagal += 1
            continue
        for k, v in t.items():
            per_tahap.setdefault(k, []).append(v)
        per_ext.setdefault(Path(p).suffix.lower(), []).append(t["dekode_draft"])
        if len(banding) < 40 and Path(p).suffix.lower() in {".jpg", ".jpeg"}:
            a = time.perf_counter()
            dekode(d, False)
            banding.append((time.perf_counter() - a, t["dekode_draft"]))

    for k, v in per_tahap.items():
        print(f"{k:14} median {st.median(v) * 1000:7.1f} ms  rata2 {st.mean(v) * 1000:7.1f} ms")
    for k, v in per_ext.items():
        print(f"dekode {k:6} n={len(v):4d} median {st.median(v) * 1000:7.1f} ms")
    if banding:
        print(f"JPEG dekode penuh {st.median(x for x, _ in banding) * 1000:.1f} ms "
              f"vs draft {st.median(y for _, y in banding) * 1000:.1f} ms (median, n={len(banding)})")
    cpu = sum(st.mean(v) for v in per_tahap.values())
    print(f"gagal: {gagal}")
    print(f"tahap A per foto: baca {dt_urut / len(isi):.3f} + cpu {cpu:.3f} = {dt_urut / len(isi) + cpu:.3f} s")
    print(f"perkiraan tahap A {len(semua)} foto, 1 proses: {(dt_urut / len(isi) + cpu) * len(semua) / 3600:.2f} jam")


if __name__ == "__main__":
    main()
