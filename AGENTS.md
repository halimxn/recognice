# Aturan AI — Recognice v2

Satu-satunya berkas aturan untuk semua AI. `CLAUDE.md` dan `GEMINI.md` hanya menunjuk ke sini.

Galeri foto lokal Windows dengan pengenalan wajah. Rancangan: `docs/superpowers/specs/2026-11-08-recognice-v2-design.md`.

## Peta kode

| Bagian | Letak |
|---|---|
| Mesin (tanpa Qt) | `app/core/` |
| Tampilan | `app/ui/qml/` (`theme/Theme.qml` satu-satunya tempat warna dan ukuran), jembatan Python di `app/ui/bridge/` |
| Model | `models/` (`MODEL.md`: sumber, hash, lisensi) |
| Ukur dan uji | `dev/bench/`, `dev/eval/`, `dev/uji/` |

## Perintah

```
.venv\Scripts\python.exe app\main.py
.venv\Scripts\python.exe -m pytest dev\uji -q
```

## Aturan

- Foto asli hanya dibaca. Tidak pernah dipindah, diubah, atau dihapus. Ekspor = menyalin, dengan jurnal.
- `app/core` tidak boleh mengimpor PySide6.
- Pekerjaan berat tidak pernah di benang UI.
- Warna dan ukuran mentah hanya di `Theme.qml`.
- Skor kemiripan bukan persen. Klaim akurasi harus punya angka dari `dev/eval`.
- Tidak ada jaringan saat aplikasi berjalan. Foto dan sidik wajah tetap di perangkat.
- Bobot InsightFace hanya untuk pemakaian pribadi nonkomersial.
- Laporkan apa adanya: yang belum diuji disebut belum diuji.
