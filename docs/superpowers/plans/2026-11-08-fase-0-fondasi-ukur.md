# Fase 0 — Fondasi dan ukur (rencana kerja)

Dikerjakan 8 Nov 2026; tersisa langkah 8 (menunggu set emas). Mengacu ke [rancangan v2](../specs/2026-11-08-recognice-v2-design.md). 
Tujuan fase: mengganti tebakan dengan angka dari laptop pemilik, dan mendapatkan kerangka kosong yang bersih.

## Langkah

1. **Bersihkan.** Tampilkan daftar jalur+ukuran yang akan dihapus (§3 rancangan), minta "ya" terakhir, hapus v1
   (`app/ build/ dist/ dev/ tools/ logs/ docs/ lama, .venv, Recognice.spec, *.cmd lama, requirements.txt lama, data/recognice.db*`).
   Pertahankan `docs/superpowers/`. Model ONNX lama disalin dulu ke `models/lama/` sebagai pembanding, dihapus di akhir fase.
2. **Lingkungan.** `uv venv` Python 3.14 (bila wheel PySide6/onnxruntime/pillow-heif ada) atau 3.13; `requirements.txt` baru; catat hasil cek wheel.
3. **Kerangka.** `AGENTS.md` (+`CLAUDE.md`/`GEMINI.md` penunjuk), `.gitignore`, `git init`, struktur §8, `app/main.py` membuka jendela QML kosong dengan `Theme.qml` (token terang/gelap).
4. **Model.** Unduh `buffalo_l` dan `antelopev2` ke folder terpisah; verifikasi SHA-256 dari rilis resmi, periksa bentuk I/O ONNX, tulis `models/MODEL.md` (sumber, hash, lisensi).
5. **Sensus + bench I/O** (E: harus terpasang; pemilik menaruh set emas mini di `dev/eval/gold/<nama>/`). Sensus ekstensi dan ukuran file (hanya nama, tanpa membuka isi) lalu `dev/bench/io.py`: baca 300 foto acak dari E: berurutan jalur vs acak; dekode penuh vs `Image.draft`; HEIC bila ada. Keluaran: detik/foto.
6. **Bench model.** `dev/bench/model.py`: SCRFD-2.5G vs 10G (waktu per foto 1280 px, jumlah wajah), embedding mbf vs w600k_r50 vs glintr100 (ms/wajah, 1 vs 2 vs 4 thread, INT8 bila dicoba). Keluaran: tabel di `dev/bench/HASIL.md`.
7. **Bench UI.** Prototipe QML `GridView` dengan 20.000 thumbnail dari model Python berpaginasi + `QQuickImageProvider` asinkron; ukur FPS gulir dan RAM di HD 520.
8. **Keputusan.** Jalankan `dev/eval` pada set emas mini; pilih detektor dan embedding **final** menurut aturan §14 dari tabel; tulis ke rancangan §6; syarat keluar Fase 0 diperiksa.

## Syarat keluar
- `dev/bench/HASIL.md` berisi angka nyata (I/O, deteksi, embedding, UI).
- Aplikasi kerangka terbuka tanpa galat; `AGENTS.md` ada; v1 hilang.
- Model terverifikasi hash. Pilihan detektor/embedding final tertulis dengan angkanya dan aturan §14.
- Jika grid QML gagal 60 fps pada 20 ribu foto: berhenti dan rancang ulang sebelum Fase 1.

## Catatan eksekusi
Dikerjakan dengan alur: rencana ini → implementasi per langkah → verifikasi (`superpowers:verification-before-completion`). Model eksekusi dipilih pemilik.
