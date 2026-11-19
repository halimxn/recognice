# Recognice v2 — Rancangan galeri foto dengan pengenalan wajah

Tanggal: 8 November 2026. Status: **draf menunggu persetujuan pemilik** (belum ada kode produk yang ditulis).
Penulis rancangan: Claude. Keputusan pemilik ditandai **[Pemilik]**, pilihan saya ditandai **[Saya]**.

## 1. Maksud

Pemilik punya ±21.800 foto (±75 GB) di HDD USB terenkripsi VeraCrypt (E:). Ia ingin **galeri foto yang enak
dilihat** dan, di atasnya, **cara paling cepat menemukan seseorang**: klik nama, lihat semua fotonya; seret
satu foto contoh, dapat foto-foto yang mirip. Semuanya lokal, tanpa internet.

Recognice v1 gagal karena: UI Qt Widgets dilukis manual (`komponen.py` 1.647 baris, `layar_galeri.py` 1.065
baris) dan bisa crash saat mulai (`data/galat_mulai.txt`); hanya 2.710 dari 21.775 foto terpindai; 721 "orang"
untuk 5.155 wajah dan hanya 1 yang bernama (pengelompokan terlalu pecah dan peninjauan terlalu berat); akurasi
tidak pernah diukur. v2 adalah **tulis ulang penuh**; kode v1 hanya dirujuk, tidak dipakai ulang.

## 2. Tujuan, bukan-tujuan, anti-tujuan

**Tujuan**
1. Galeri terbuka dalam < 1 detik dan lancar di 20 ribu+ foto pada laptop pemilik.
2. Menemukan orang dalam ≤ 3 klik: Orang → klik avatar, atau Cari → seret foto contoh.
3. Pemberian nama cepat: ratusan kelompok diselesaikan dengan keyboard, bukan satu per satu dengan mouse.
4. Akurasi **terukur** pada label milik pemilik, bukan klaim dari benchmark penyedia model.
5. UI rapi, konsisten, dan terasa sebagai aplikasi desktop selesai (satu sistem token, satu pustaka komponen).

**Bukan-tujuan** (ditunda atau tidak pernah): video (fase akhir), peta/GPS, album buatan, edit foto, sinkronisasi/awan,
mobile, merapikan/mengganti nama/memindah file (itu tugas RapikanAlbum/Zenfile).

**Anti-tujuan** (kegagalan meski "jalan"): dua orang berbeda tergabung diam-diam; UI membeku saat memindai;
foto asli tersentuh; angka akurasi yang tidak bisa dibuktikan; kode tampilan berlapis yang tidak bisa dirawat.

## 3. Keputusan yang sudah ditetapkan

| Hal | Keputusan |
|---|---|
| Tampilan | **[Pemilik]** PySide6 + **QML (Qt Quick)**. Tanpa server, port, atau webview. |
| Model wajah | **[Pemilik]** Boleh bobot InsightFace (riset/nonkomersial), aplikasi hanya pribadi. |
| Cakupan | **[Pemilik]** Foto dulu; video fase terakhir. |
| Foto asli | **[Pemilik]** Hanya dibaca. Ekspor = menyalin ke folder baru, dengan jurnal. Tidak pernah pindah/hapus/ubah. |
| Aturan lama | **[Pemilik]** Diabaikan; v2 punya aturan sendiri (§12). |
| Kode v1 | **[Pemilik, 8 Nov 2026]** **Dihapus**, tidak diarsipkan (`app/`, `build/`, `dist/`, `dev/`, `tools/`, `logs/`, `.venv`, `.spec`, `.cmd` lama, `docs/` lama, `data/recognice.db*`). Dilakukan saat eksekusi, setelah pemilik memberi aba-aba. Model ONNX lama tidak dihapus sampai pembanding Fase 0 selesai. |
| Unduh model | **[Pemilik]** Boleh: `buffalo_l` (±275 MB) dan `antelopev2` (±344 MB) dari rilis resmi InsightFace; hash dan lisensi diperiksa dulu. Dilakukan di Fase 0. |
| Lokasi data | **[Pemilik]** `data/` di samping aplikasi, dapat dipindah (mis. ke volume VeraCrypt). |
| Bahasa | **[Pemilik]** Indonesia dulu, struktur `qsTr` siap Inggris. |
| Set berlabel | **[Pemilik]** Bersedia melabel ±20 orang × ±10 foto (±1 jam) lewat aplikasi. |
| Nama & gaya | **[Pemilik]** Nama tetap "Recognice"; huruf Inter, aksen teal, kanvas netral gelap/terang. |
| Pindai awal | **[Pemilik]** Hanya `E:\01 Foto dan Video`; jeda otomatis saat baterai. |
| Eksekusi | **[Pemilik]** Rancangan dilanjutkan dulu; pemilik ditanya sebelum berpindah ke mode eksekusi (model Opus). |

## 4. Arsitektur

```
 QML (tampilan, deklaratif)         Python (UI-bridge tipis)            Python core (tanpa Qt)
 ───────────────────────────        ────────────────────────────        ──────────────────────────
 Theme.qml (token tunggal)    ◄──►  models: PhotoModel, PeopleModel ◄──► library  (SQLite, kueri)
 components/ (Button, Chip,         image provider (thumbnail async)    scanner   (temukan, baca sekali)
   Avatar, Dialog, Toast…)          controllers: scan, review, search   faces     (deteksi, sejajar, embed)
 views/ (Photos, People, Search…)                                       cluster   (kelompok + koreksi)
                                                                        search    (matmul cosine)
                                                                        export    (salin + jurnal)
```

- **`core/` tidak mengimpor Qt**: bisa diuji dengan pytest dan dipakai alat evaluasi. Qt hanya di `ui/`.
- **Satu proses UI + kolam proses pekerja** (`ProcessPoolExecutor`) untuk dekode gambar dan ONNX. Sesi ONNX
  dibuat sekali per pekerja; pekerja dibatasi (i5-6200U = 2 inti/4 thread). UI tidak pernah memanggil I/O berat.
- **Qt Quick dipercepat GPU Intel HD 520** lewat scene graph; daftar foto memakai `ListView/GridView`
  bermodel Python yang dipaginasi (jendela data), bukan membuat 20 ribu objek.
- **Stack**: Python 3.14, PySide6 6.12, onnxruntime 1.31 (CPU), NumPy, Pillow + pillow-heif. Semua sudah
  terbukti terpasang di `.venv` v1. **Belum diperiksa**: apakah seluruh wheel punya build Python 3.14 untuk
  PyInstaller (diperiksa di Fase 0).

### Penyimpanan

SQLite (WAL) di `data/library.db`, thumbnail di `data/thumbs/` (cakram), embedding dimuat ke satu matriks NumPy
float16 di memori (45 ribu × 512 ≈ 46 MB).

| Tabel | Isi utama |
|---|---|
| `source` | folder akar, label drive, terakhir terhubung |
| `photo` | jalur relatif ke source, ukuran, mtime, lebar/tinggi, `taken_at` (EXIF, cadangan mtime), status |
| `face` | photo_id, kotak, 5 titik, skor deteksi, kualitas, embedding (BLOB fp16), person_id, status penetapan |
| `person` | nama, wajah sampul, disembunyikan/difavoritkan |
| `constraint` | pasangan wajah/orang yang **pasti sama** atau **pasti beda** (koreksi pemilik, bertahan di setiap pengelompokan ulang) |
| `scan_run` | riwayat, galat per file |

**Galeri tetap bisa dijelajahi saat drive VeraCrypt tidak terpasang**: thumbnail 256 px dan 1024 px ada di
cakram lokal; hanya "buka asli" yang menunggu drive. Ini penting untuk pemakaian sehari-hari.

## 5. Mesin pemindaian (hemat I/O HDD USB)

Pembatas nyata (diukur v1, `docs/baseline.md`): 0,40–0,51 detik/foto di HDD USB = batas I/O, bukan model.
Maka desainnya "baca satu kali, kerjakan semuanya":

1. **Temukan**: `os.scandir`, bandingkan ukuran+mtime dengan DB; hanya yang baru/berubah diproses. Pindai ulang tanpa perubahan < 1 detik.
2. **Urut menurut jalur** saat membaca (mengurangi lompatan kepala HDD).
3. **Satu pembacaan, satu dekode** per foto di pekerja: `Image.draft()` untuk JPEG (dekode skala 1/2–1/8, sangat cepat),
   koreksi orientasi EXIF, hasilnya dipakai untuk (a) thumbnail 256 dan 1024, (b) citra input deteksi (sisi panjang ≤ 1280).
4. **Dua tahap prioritas**: tahap A (metadata+thumbnail) selesai dulu → **galeri langsung terisi dan bisa dipakai**;
   tahap B (wajah) berjalan di latar, bisa dijeda, dilanjutkan setelah restart, dan mengutamakan foto yang sedang terlihat.
5. Kegagalan per file dicatat dan tidak menghentikan pemindaian; drive terlepas di tengah jalan = jeda, bukan galat.
6. Jeda otomatis di baterai (opsi), laptop dijaga tetap terjaga selama bekerja.

Perkiraan **saya (belum diukur)**: tahap A ±0,15–0,3 dtk/foto bila dekode draft menekan CPU → ±1–2 jam untuk 21 ribu foto
karena I/O. Tahap B bergantung model (§6). Angka ini jadi target ukur di Fase 0, bukan janji.

## 6. Pengenalan wajah: model dan sistem

### Pilihan model
| Peran | Kandidat | Catatan |
|---|---|---|
| Deteksi + 5 titik | **SCRFD-10G** (`det_10g`) | Dipakai buffalo_l & antelopev2. Lebih tahan wajah kecil/miring daripada 2.5G terpasang. |
| Embedding (utama) | **glintr100** (antelopev2, ResNet100 Glint360K) vs **w600k_r50** (buffalo_l, ResNet50 WebFace600K) | Keduanya papan atas model terbuka; pemenang ditentukan **ukuran pada foto pemilik**. |
| Pembanding | MobileFaceNet buffalo_m (terpasang v1) | Acuan "sebelum". |
| Alternatif dicatat | AdaFace (lebih tahan kualitas rendah) | Hanya bila hasil ukur menunjukkan wajah buram jadi masalah utama. |

Sumber yang saya tinjau: panduan InsightFace menaruh R50/R100/glintr100 pada pita IJB-C TAR@FAR1e-4 ≈ 95–97,5 %;
**tidak ada perbandingan langsung antelopev2 vs buffalo_l yang bisa saya verifikasi**. Karena itu saya tidak memilih
dari kertas: **Fase 0 membuat alat uji** yang membandingkan ketiganya pada set berlabel pemilik. Kesetaraan lisensi:
semua bobot InsightFace nonkomersial (sesuai keputusan pemilik).
Perkiraan biaya CPU **[Saya, belum diukur]**: R50 ±0,1–0,2 dtk/wajah, R100 ±0,25–0,4 dtk/wajah. Untuk ±45 ribu wajah
itu ±1,5–3 jam (R50) atau ±3–5 jam (R100), sekali jalan di latar. Bila R100 tidak memberi kenaikan yang terukur,
pakai R50. Kuantisasi INT8 dicoba hanya bila akurasinya terbukti tidak turun.

### Dari wajah ke "orang" — rancangan yang menghindari kegagalan v1
1. **Gerbang kualitas**: wajah kecil (< 40 px), skor deteksi rendah, buram (varian Laplacian wajah), atau miring ekstrem
   diberi bendera. Wajah kualitas rendah **tidak boleh membentuk kelompok**; mereka hanya dilampirkan setelahnya.
2. **Kelompok awal** dari wajah berkualitas: graf k-tetangga-terdekat (matmul per blok, 45 ribu wajah dalam menit),
   sisi hanya jika di atas ambang dan **saling tetangga**; komponen terhubung dengan penjaga ukuran/kepadatan.
   Batasan **tidak mungkin sama**: dua wajah di foto yang sama tidak boleh sekelompok.
3. **Orang = beberapa prototipe** (≤ K=5 pusat berbobot kualitas), bukan satu rerata, supaya anak→dewasa,
   dengan/tanpa kacamata tidak memecah orang.
4. **Penugasan wajah baru** ke prototipe terdekat dengan margin dari kandidat kedua; ragu → kolam **"Belum yakin"**,
   tidak dipaksa masuk. Salah pisah murah ditinjau, salah gabung tidak.
5. **Koreksi pemilik = batasan permanen** (`constraint`): "ini dia", "bukan dia", "gabungkan", "pisahkan" tidak
   hilang saat model/ambang diganti atau pengelompokan diulang.
6. **Skor jujur**: pita *Sangat mirip / Mirip / Mungkin* dikalibrasi dari pasangan berlabel pemilik (precision
   empiris per pita), bukan cosine mentah dan bukan "persen".
7. **Evaluasi bawaan**: alat `dev/eval` menghitung precision/recall pasangan dan B-cubed F1 pada set emas. Ini
   syarat keluar Fase 6 dan dipakai tiap kali model/ambang berubah. Set emas dibuat lewat alur peninjauan aplikasi
   (±20 orang × ±10 foto, ±1 jam).

### Pencarian
- **Nama**: kotak cari global (orang, folder, tanggal).
- **Foto contoh**: seret/pilih foto → deteksi → pilih wajah → peringkat orang dan peringkat wajah (matmul, < 50 ms).
- **"Mirip wajah ini"** dari lightbox, dan **filter orang berganda** ("foto berisi A *dan* B").
- Brute-force matmul cukup sampai ±100 ribu wajah; tanpa FAISS/HNSW (YAGNI).

## 7. Desain UI/UX

**Prinsip**: foto adalah warna; antarmuka tenang. Kanvas netral (gelap hampir hitam / terang hangat), satu aksen,
tanpa kartu di dalam kartu, tanpa dekorasi. Disiplin sistem RapikanAlbum dipertahankan (token tunggal, skala jarak
4/8/12/16/24/32/40, tinggi baris tetap, pemeriksaan otomatis), tetapi **bukan** tampilan utilitas CCleaner: ini
galeri. **[Saya]** huruf Inter (OFL, dibundel, offline) dan aksen teal; bisa diganti saat desain visual.

**Kerangka**: rel kiri ikon+label (Foto · Orang · Cari · Sumber · Pengaturan), bilah atas dengan kotak cari global
dan *chip* status pindai (klik → rincian/jeda). Bilah judul Windows asli.

| Layar | Isi dan perilaku |
|---|---|
| **Foto** | Baris rata (justified) menjaga rasio gambar, dikelompokkan per hari/bulan, *scrubber* tahun-bulan di tepi kanan, slider ukuran, pilih banyak (kotak centang, Shift, seret), jendela data berpaginasi, thumbnail dimuat saat terlihat |
| **Lightbox** | Pratinjau 1024 langsung, asli menyusul; zoom/pan halus; tombol `F` menampilkan kotak wajah dengan nama; klik wajah → beri nama / "Bukan dia"; panah/gulir antar-foto; strip foto; panel info (tanggal, folder, ukuran) |
| **Orang** | Kisi avatar bundar menurut jumlah foto, sematan favorit; spanduk **"N kelompok perlu ditinjau"** membuka *Peninjauan cepat*; halaman orang: sampul, jumlah+rentang tanggal, tab *Foto* / *Wajah* (bersihkan: pilih yang salah → "Bukan dia"), "Mungkin orang yang sama" (bandingkan berdampingan), sering muncul bersama |
| **Peninjauan cepat** | Satu kelompok per layar, sampel wajah besar, ketik nama + `Enter` (autokomplit nama ada), `Tab` lewati, `M` gabung ke saran, `X` pecah; ratusan kelompok selesai dengan keyboard; progres terlihat |
| **Cari** | Kotak besar + zona seret "Foto contoh"; *chip* orang/tanggal/folder; hasil dengan pita kemiripan |
| **Sumber** | Pohon folder, status per sumber, tombol pindai/jeda, penanda drive "tidak terhubung" (galeri tetap jalan dari cache) |
| **Pengaturan** | Tema (gelap/terang/Windows), performa (pekerja, jeda di baterai), model aktif, data (lokasi, ukuran cache, cadangan/pulihkan), lanjutan (ambang) tersembunyi di balik "Lanjutan" |
| **Awal** | Pertama dibuka: pilih folder → "Mulai" → galeri terbuka dalam hitungan detik, wajah menyusul di latar |

Keadaan kosong, galat, dan memuat dirancang untuk **setiap** layar (bukan tambahan akhir). Semua bisa dioperasikan
keyboard; kontras memenuhi WCAG AA; fokus terlihat. Teks lewat `qsTr` (Indonesia dulu, Inggris menyusul tanpa ubah kode).

**Anggaran kinerja** (diuji otomatis, laptop pemilik): gulir 60 fps pada 20 ribu foto; RAM diam < 500 MB;
cache thumbnail memori ≤ 200 MB; buka aplikasi → galeri tampil < 1 dtk.

## 8. Struktur proyek

```
Recognice/
  AGENTS.md  CLAUDE.md  GEMINI.md        aturan satu sumber (§12)
  app/
    main.py
    core/   library.py scanner.py thumbs.py faces.py quality.py cluster.py search.py export.py db.py
    ui/     bridge/*.py   qml/Theme.qml  qml/components/*.qml  qml/views/*.qml   assets/
  models/   (ONNX + MODEL.md: hash, lisensi, bentuk I/O)
  data/     library.db  thumbs/           (dapat dipindah; bawaan di samping aplikasi)
  dev/      eval/ bench/ uji/ screenshots/  docs/
```

## 9. Fase dan syarat keluar

| Fase | Isi | Syarat keluar (diukur) |
|---|---|---|
| **0 Fondasi & ukur** | Arsipkan v1; kerangka; ambil model (izin, §11); `bench`: kecepatan dekode HDD, ONNX R50/R100/10G/2.5G di CPU ini; cek wheel Py3.14; AGENTS.md | Tabel kecepatan nyata; model dipilih sementara; aplikasi kosong terbuka |
| **1 Galeri tanpa wajah** | Pemindai A, DB, thumbnail, Foto + Lightbox, Sumber, tema | 21 ribu foto digulir 60 fps; indeks ulang < 1 dtk; drive dicabut → tetap bisa dijelajahi |
| **2 Pipa wajah** | Deteksi, penyejajaran, embedding, kualitas, bisa dilanjutkan | Semua foto terproses tanpa membekukan UI; throughput sesuai Fase 0 |
| **3 Orang** | Pengelompokan, Orang, Peninjauan cepat, koreksi/batasan, gabung/pisah | 100 kelompok dinamai < 10 menit; koreksi bertahan saat pindai ulang |
| **4 Cari** | Nama, foto contoh, mirip-wajah, filter orang | Hasil < 100 ms; pencarian foto contoh menemukan orang yang benar pada set emas |
| **5 Poles** | Awal, Pengaturan, a11y, i18n, ekspor salin+jurnal, cadangan, pengemasan portabel | Uji layar otomatis lulus di 2 tema; `Kemas` jalan di mesin bersih |
| **6 Evaluasi** | Set emas, kalibrasi pita, tentukan model/ambang akhir | Laporan precision/recall/B-cubed; ambang dibekukan dengan angka |
| 7 (opsional) | Video: beberapa frame kunci per klip | — |

Setiap fase: rencana tertulis (superpowers:writing-plans), uji untuk logika `core`, tangkapan layar offscreen untuk UI,
dan **tidak lanjut** bila syarat keluar belum tercapai. Fase 1 memberi galeri yang sudah berguna sebelum wajah ada.

## 10. Risiko

| Risiko | Penanganan |
|---|---|
| Embedding R100 terlalu lambat di i5-6200U | Ukur di Fase 0; R50; INT8 hanya bila terukur aman; hanya wajah berkualitas diembed penuh |
| I/O HDD USB mendominasi | Baca sekali, urut jalur, draft decode, tahap A mandiri dari tahap B |
| QML lambat di HD 520 / driver | Prototipe grid 20 ribu foto di Fase 0 sebelum membangun yang lain |
| Wheel Py3.14 belum lengkap untuk kemasan | Cek Fase 0; cadangan: Python 3.13 untuk kemasan |
| Pemilik jenuh menamai | Peninjauan cepat via keyboard, saran gabung, kolam "belum yakin", orang terbanyak lebih dulu |
| Akurasi nyata tak diketahui | Set emas + alat eval sebagai syarat keluar |
| Data biometrik | Semuanya lokal; lokasi `data/` dapat diarahkan ke volume VeraCrypt |

## 11. Izin yang masih perlu dari pemilik

Sudah diizinkan (§3), **belum dilakukan** sampai pemilik memberi aba-aba eksekusi:
- Mengunduh `buffalo_l` (≈ 275 MB) dan `antelopev2` (≈ 344 MB); hash dan lisensi diperiksa sebelum dipakai.
- Menghapus kode v1 dan data lama (daftar di §3). Penghapusan permanen: sebelum jalan, saya tampilkan daftar jalur dan ukurannya sekali lagi.

## 12. Aturan AI untuk proyek baru (menggantikan semua yang lama)

Satu berkas `AGENTS.md` di akar; `CLAUDE.md`/`GEMINI.md` hanya menunjuk ke sana. Isinya singkat: peta kode, perintah
jalan/uji, aturan "foto asli hanya dibaca", dan batas `core` tanpa Qt. Dibuat pada Fase 0.

## 13. Skill dan agen (dikerjakan di sesi yang sama)

Terpasang secara global pada **Claude** (`~/.claude/skills`, dibaca juga oleh **OpenCode**), **Codex** (`~/.codex/skills`),
dan **Antigravity** (`~/.gemini/antigravity/skills`): `caveman`, `ultracave`, `megacave`, `grill-me`, `grilling`
(sumber: JuliusBrussee/caveman dan mattpocock/skills, keduanya MIT; isinya saya baca sebelum dipasang, tanpa perintah
jaringan/eksekusi). `ponytail` sudah ada di semua agen. `rtk` (v0.49.0): hook Claude, Codex, Gemini aktif; plugin
OpenCode baru dipasang (butuh rtk lebih baru dari 0.51 agar penulisan ulang berlaku; sampai itu perintah lewat apa adanya).

## 14. Hasil pemeriksaan pembangun (8 Nov 2026)

Seorang pembangun independen membaca dokumen ini tanpa konteks percakapan dan mengajukan 10 pertanyaan. Semua kecuali
dua dijawab di sini. Yang ditandai **[Saya]** adalah pilihan saya; pemilik boleh membantah.

**Perangkat dan lingkungan.** Mesin pengembangan = laptop pemilik (Windows 11 LTSC, i5-6200U 2 inti/4 thread, RAM 11,9 GB,
Intel HD 520 + GeForce 920MX yang tidak dipakai). Semua anggaran kinerja diukur di mesin ini. Drive E: tidak terpasang
saat rancangan ini ditulis; sensus format dan bench I/O dikerjakan di Fase 0 saat E: dibuka.

**Aturan memilih model [Saya].** Model embedding **diputuskan di Fase 0**, bukan Fase 6, memakai *set emas mini* tanpa alat:
pemilik menaruh ±10 orang × ±6 foto di `dev/eval/gold/<nama>/` (±15 menit). Pilih glintr100 (R100) hanya bila TAR@FAR=1e-3
pasangan naik ≥ 1,5 poin mutlak dibanding w600k_r50 atau ia memperbaiki kasus wajah miring/buram yang nyata; selain itu R50
(separuh biaya CPU). Fase 6 hanya menyetel ambang, bukan mengganti model. Kolom `face.model_id` menandai model embedding, jadi
penggantian kelak = embed ulang terkontrol, bukan skema rusak.

**Target akurasi [Saya, untuk disetujui pemilik].**
| Ukuran (pada set emas, 30 % dipisah dari penyetelan ambang) | Target |
|---|---|
| Presisi B-cubed kelompok yang ditetapkan otomatis | ≥ 0,98 |
| Wajah berlabel yang berhasil ditetapkan (recall, di luar "Belum yakin") | ≥ 0,85 |
| Pita *Sangat mirip* / *Mirip* / *Mungkin*: presisi pasangan | ≥ 99 % / ≥ 95 % / ≥ 70 % |
| Pencarian foto contoh: orang benar ada di 5 teratas | ≥ 95 % |
| Kelompok yang mencampur dua orang berbeda | ≤ 1 per 100 kelompok |
Tidak ada "nol salah gabung" yang bisa dijanjikan; yang dijamin: salah gabung selalu bisa dipisah dan koreksi bertahan.

**Set emas [Saya].** Disimpan terpisah (`data/gold.json`), tidak ikut dibangun ulang bersama DB, dan wajahnya tidak dipakai
menyetel ambang yang sama dengan yang dievaluasi (pemisahan 70/30). Berisi **negatif** juga: wajah orang lain/asing dan
kerabat mirip. Fase 0 memakai versi folder (di atas); Fase 3 menambah mode "Set emas" di aplikasi untuk memperluasnya.

**Identitas foto [Saya].** `photo` memakai (source, jalur relatif) dan **SHA-1 isi** yang dihitung dari byte yang sudah dibaca untuk
dekode (nol I/O tambahan). Foto yang dipindah/diganti nama dicocokkan lewat hash dan membawa wajah, nama, dan koreksinya.
Source dikenali dari label+nomor seri volume, jadi huruf drive berubah tidak membuat semuanya "baru". File hilang ditandai
`hilang`, tidak dihapus; wajah dan nama tetap sampai pemilik memilih "bersihkan".

**Tumpukan dan kemasan [Saya].** Satu versi Python untuk pengembangan dan kemasan: 3.14 bila semua wheel (PySide6, onnxruntime,
Pillow, pillow-heif, PyInstaller) ada, bila tidak 3.13 untuk keduanya. Versi dipaku di `requirements.txt`. Kemasan = PyInstaller
mode folder portabel (seperti sebelumnya), tanpa installer. Memasang paket dari PyPI perlu internet: **butuh izin pemilik** (§ pertanyaan).

**Model orang [Saya].** Batasan hanya pada **wajah**; tindakan tingkat orang ("gabungkan", "pisahkan") diterjemahkan menjadi
batasan wajah. "Belum yakin" = status wajah (`person_id` kosong, `state='uncertain'`), bukan orang. Konflik: batasan pemilik
selalu menang atas algoritme; antara dua batasan bertentangan, yang terbaru menang dan konflik dilaporkan. Pengelompokan =
komponen terhubung lalu dipecah di tempat ada *cannot-link*. K=5, ambang, dan margin diturunkan dari set emas, bukan ditebak.

**Pembaruan dan stabilitas [Saya].** Pindai baru hanya **menugaskan** wajah baru ke prototipe yang ada; pengelompokan global
hanya berjalan pada kolam yang belum ditetapkan. Orang yang pernah disentuh pemilik (diberi nama, digabung, dikoreksi)
**terkunci**: ID dan anggotanya stabil. Ganti model = embed ulang semua wajah, bangun ulang yang tak terkunci, dan cocokkan
ulang orang terkunci lewat wajah yang sudah dikonfirmasi pemilik.

**Cadangan dan migrasi [Saya].** Cadangan = `library.db` + `gold.json` + pengaturan (thumbnail bisa dibuat ulang, tidak ikut),
memakai API backup SQLite ke folder pilihan pemilik, bernama dengan cap waktu. Skema memakai `PRAGMA user_version` dengan
skrip migrasi berurutan sejak versi pertama.

**Format [Saya].** Pemindai menerima JPEG, PNG, WebP, HEIC/HEIF; RAW dan GIF dilewati dulu. Video di folder yang sama dilewati dan
dihitung ("N video dilewati"). Jalur cepat `Image.draft()` hanya JPEG; bench Fase 0 mengukur HEIC/PNG terpisah dan perkiraan
waktu §5 dikoreksi dengan sensus format nyata.

## 15. Hasil ukur Fase 0 (8 Nov 2026) — menggantikan perkiraan di §5 dan §6

Rincian: `dev/bench/HASIL.md`. Perkiraan saya sebelumnya keliru pada dua hal:

- **HDD bukan pembatas utama.** Baca 78 ms/foto; dekode CPU yang dominan. Tahap A 0,235 dtk/foto = 1,42 jam dengan 1 proses. Pekerja paralel berguna; total baca ±28 menit adalah batas bawahnya.
- **R100 5,4x lebih mahal daripada R50**, bukan 2x: 884 vs 164 ms/wajah. Tahap B penuh ±3,2 jam dengan R50 dan ±11,4 jam dengan R100.

Karena itu aturan §14 diketatkan **[Saya]**: R100 hanya layak bila keunggulannya pada set emas jelas (selisih TAR@FAR=1e-3 ≥ 1,5 poin) **dan** pemilik menerima pemindaian pertama ±11 jam. Pilihan sementara: **SCRFD-10G kanvas 640 + R50** (3,2 jam). Kanvas 1280 (4x lebih lambat) ditolak kecuali set emas menunjukkan wajah penting terlewat.

Sensus: 21.775 foto, 93 % JPEG; 268 RAW (`.cr2`) dilewati dulu. Grid QML 20 ribu thumbnail lolos 60 fps di HD 520 dengan RAM ±190 MB.
