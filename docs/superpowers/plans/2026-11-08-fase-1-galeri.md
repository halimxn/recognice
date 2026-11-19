# Fase 1 — Galeri tanpa wajah (rencana kerja)

> Dikerjakan inline (superpowers:executing-plans). Langkah TDD per modul `core`.

**Goal:** Galeri foto yang bisa dipakai: pindai folder, gulir seluruh pustaka, buka lightbox, kelola sumber, tetap jalan tanpa drive.

**Architecture:** `core` tanpa Qt: SQLite, pemindai (satu pembaca berurutan + kolam proses dekode), thumbnail berdasarkan SHA-1, tata letak baris rata murni. QML menampilkan jendela baris tetap yang digeser Python, sehingga tinggi konten tepat dan scrubber akurat.

**Tech Stack:** Python 3.14, PySide6-Essentials 6.12, Pillow, pillow-heif, SQLite.

**Spec:** `docs/superpowers/specs/2026-11-08-recognice-v2-design.md`

## Global Constraints

- Foto asli hanya dibaca. `app/core` tanpa PySide6. Warna/ukuran mentah hanya di `Theme.qml`.
- Format: JPEG, PNG, WebP, HEIC/HEIF. RAW, GIF, video dilewati.
- Identitas foto: (source, jalur relatif) + SHA-1 isi dari byte yang sudah dibaca. Source dikenali dari nomor seri volume.
- Thumbnail di `data/thumbs/`: tinggi 256 dan sisi panjang 1024.
- Jeda otomatis saat baterai. Laptop dijaga terjaga selama memindai.

## Review Focus

1. Drive tercabut di tengah pindai: berhenti, tidak ada foto ditandai hilang.
2. Sebagian folder tak terbaca: tidak ada foto ditandai hilang pada putaran itu.
3. File rusak: dicatat `gagal`, pindai lanjut.
4. Foto dipindah/diganti nama: baris lama dipakai ulang lewat SHA-1 (`id` tetap).
5. EXIF tanggal rusak (`0000:00:00`): jatuh ke tanggal ubah, tidak gagal.

## Tugas

### 1. `core/db.py`
`buka(jalur) -> sqlite3.Connection`: WAL, `foreign_keys`, migrasi berurutan lewat `PRAGMA user_version`. Tabel `source(id, serial, akar_relatif, huruf_terakhir, label, terakhir_pindai)`, `photo(id, source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, sumber_tanggal, status, galat)`, unik `(source_id, rel)`. Indeks `(status, taken_at DESC, id DESC)` dan `sha1`.
Uji: `test_migrasi_idempoten`, `test_versi_skema`.

### 2. `core/thumbs.py`
`jalur(akar, sha1, ukuran)`, `buat(gambar, akar, sha1)`. Uji: `test_tinggi_256`, `test_sisi_panjang_1024`, `test_tidak_memperbesar`.

### 3. `core/scanner.py`
`olah(jalur_nama, data, akar_thumb) -> dict` (proses pekerja), `temukan(akar) -> (dict rel->(ukuran,mtime_ns), ada_galat)`, `Pemindai(db, akar_thumb, pekerja).jalankan(source_id, batal, jeda, lapor) -> Ringkasan`. Uji: Review Focus 1–5, `test_pindai_ulang_tanpa_perubahan`, `test_format_lain_dilewati`, `test_folder_sistem_dilewati`.

### 4. `core/layout.py`
`susun(foto, lebar, tinggi, jarak, kepala) -> Tata` murni; baris rata tinggi tetap per baris, baris terakhir per hari tidak meregang. Uji: `test_lebar_baris_pas`, `test_kepala_per_hari`, `test_y_berurutan`, `test_baris_di_y`.

### 5. `core/library.py`
`semua_foto(db)`, `sumber(db)`, `tambah_sumber(db, akar)`, `hapus_sumber(db, id)`. Uji: urutan terbaru dulu, hanya `ok`.

### 6. `ui/bridge` + QML
`Galeri` (tata + jendela baris), `Pindai` (benang latar, sinyal progres), layar Foto, Lightbox, Sumber, keadaan kosong. Uji: QML terbuka tanpa galat; tangkapan layar nyata pada 1366x768 di dua tema.

### 7. Verifikasi syarat keluar
Pindai pustaka nyata (`E:\01 Foto dan Video`), ukur FPS pada data nyata, pindai ulang < 1 dtk, drive tidak terpasang tetap bisa dijelajahi.
