# Model wajah

Semua model berjalan offline lewat ONNX Runtime CPU. Berkas ada di folder ini.

| Berkas | Ukuran | SHA-256 | Masukan | Keluaran |
|---|---:|---|---|---|
| `det.onnx` | 3.292.009 | `041f73f47371333d1d17a6fee6c8ab4e6aecabefe398ff32cca4e2d5eaee0af9` | `input.1` `[1,3,?,?]` float32 | 9 tensor: skor/bbox/5 titik pada stride 8, 16, 32 |
| `det_500m_cadangan.onnx` | 2.524.817 | `5e4447f50245bbd7966bd6c0fa52938c61474a04ec7def48753668a9d8b4ea3a` | sama | Detektor lama; disimpan untuk pembanding, tidak dipakai. |
| `rec.onnx` | 13.616.099 | `9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f` | `input.1` `[?,3,112,112]` float32 | `516` `[N,512]` sidik ArcFace |
| `genderage.onnx` | 1.322.532 | `4fde69b1c810857b88c64a335084f1c3fe8f01246c9a191b48c7bb756d6652fb` | `data` `[?,3,96,96]` float32 | `fc1` `[N,3]`: dua logit gender + usia/100. **Tidak dipakai lagi** (dihapus dari jalur pindai/cari karena memperlambat). |

Catatan:

- Model aktif adalah kombinasi **SCRFD-2.5G + ArcFace MobileFaceNet (W600K-MBF)**. Ini bukan paket resmi `buffalo_m` utuh: katalog InsightFace saat ini mendefinisikan `buffalo_m` dengan recognizer ResNet50. Bobot aktif berasal dari rilis InsightFace/yakhyo dan lisensinya tetap perlu diperiksa sebagai bobot pretrained.
- Detektor lama (500M) salah menganggap fasad bangunan dan pixel-art sebagai wajah; 2.5G tidak. Biaya CPU ±2× lebih tinggi (≈100–140 ms/foto), tetapi jauh lebih sedikit salah deteksi.
- `AMBANG_DETEKSI` dinaikkan ke 0,55 dan ukuran wajah minimum bawaan 48 px. Pada gambar rumah/peta pixel-art yang diuji, hasilnya 0 kotak wajah.
- `det.onnx` memakai bentuk masukan dinamis, tetapi anchor keluarannya dihitung untuk kanvas 640×640. Jangan mengubah `UKURAN_DETEKSI` tanpa menguji ulang pasca-proses.
- `rec.onnx` menerima batch dinamis; batch 1, 4, dan 16 sudah diuji.
- `genderage.onnx` tidak dipakai lagi: model gender/usia mengeluarkan aplikasi dari jalur pindai dan cari.
- Bobot InsightFace yang terpasang memiliki batas penggunaan nonkomersial. Lihat `LISENSI.txt`.
- Setiap foto menyimpan `foto.model_versi`. Saat model diganti, `VERSI_MODEL` di `engine/wajah.py` dinaikkan dan foto lama otomatis diproses ulang satu kali, tanpa kehilangan nama orang.
- `msvcp140.dll` dan `msvcp140_1.dll` adalah runtime Visual C++ yang disertakan agar ONNX Runtime bisa dimuat di Windows tanpa VC++ terpasang.

## Memverifikasi

```bat
.venv\Scripts\python.exe tools\inspeksi_model.py
```

Skrip itu mencetak nama/bentuk/tipe masukan-keluaran, ukuran, dan SHA-256. Bila hash berubah, sidik lama tidak sebanding; naikkan versi model dan minta pemindaian ulang.
