# Model wajah

Bobot InsightFace: **hanya untuk riset/pemakaian pribadi nonkomersial**. Jangan didistribusikan sebagai produk.

| Berkas | Peran | Sumber (rilis `model-zoo` deepinsight/insightface) | SHA-256 arsip resmi (cocok) |
|---|---|---|---|
| `buffalo_l/det_10g.onnx` | SCRFD-10G, deteksi + 5 titik | `buffalo_l.zip` | `80ffe37d8a5940d59a7384c201a2a38d4741f2f3c51eef46ebb28218a7b0ca2f` |
| `buffalo_l/w600k_r50.onnx` | ArcFace ResNet50 WebFace600K, 512 dimensi | `buffalo_l.zip` | sama |
| `antelopev2/glintr100.onnx` | ArcFace ResNet100 Glint360K, 512 dimensi | `antelopev2.zip` | `8e182f14fc6e80b3bfa375b33eb6cff7ee05d8ef7633e738d1c89021dcf0c5c5` |
| `lama/det.onnx`, `lama/rec.onnx` | SCRFD-2.5G dan MobileFaceNet (buffalo_m), pembanding sementara | v1 | dihapus setelah evaluasi set emas |
| `runtime/msvcp140*.dll` | Runtime Visual C++ untuk ONNX Runtime; Windows ini tidak memilikinya | v1 | wajib ikut kemasan |

Masukan deteksi: RGB, `(x-127.5)/128`, kanvas persegi kelipatan 32. Keluaran 9 tensor (skor, kotak, titik; stride 8/16/32; 2 anchor per sel).
Masukan embedding: RGB 112x112 hasil penyejajaran 5 titik, `(x-127.5)/127.5`. Keluaran dinormalisasi L2.

## Keputusan model (13 November 2026)

Dipakai: `buffalo_l/det_10g.onnx` (kanvas 640, lalu deteksi ulang kanvas 192 per wajah) + `buffalo_l/w600k_r50.onnx`.
R100 dan MobileFaceNet sudah dibandingkan pada pustaka pemilik: lihat `dev/bench/HASIL.md`, bagian "Model pengenal". R100 tidak dipakai karena 4,4x lebih lambat tanpa selisih yang berarti.
Tanda model di `core/pipa_wajah.py` (`MODEL`) harus diganti setiap kali cara memotong wajah atau modelnya berubah; semua foto lalu diproses ulang dan nama orang pada wajah lama ikut hilang.
