# Hasil ukur Fase 0

Diukur 8 November 2026 di laptop pemilik: i5-6200U 2 inti/4 thread, RAM 11,9 GB, Intel HD 520, ONNX Runtime CPU.
Pustaka `E:\01 Foto dan Video` (HDD USB, VeraCrypt). Skrip: `dev/bench/`.

## Sensus (`sensus.py`, 7,9 detik untuk 24.273 file)

| Jenis | Jumlah | Ukuran | Status |
|---|---|---|---|
| `.jpg` + `.jpeg` | 20.311 | 77,7 GB | dipindai |
| `.png` | 1.123 | 0,4 GB | dipindai |
| `.webp` | 231 | 0,1 GB | dipindai |
| `.heic` | 110 | 0,2 GB | dipindai |
| `.cr2` (RAW) | 268 | 6,5 GB | dilewati dulu |
| `.mp4 .mov .3gp .mkv` | 1.704 | 110,5 GB | dilewati sampai fase video |

21.775 foto terpindai. 93 % JPEG, jadi jalur cepat `Image.draft` berlaku hampir di semua foto.

## Tahap A per foto (`io.py`, 2 x 300 foto, 1 proses)

| Langkah | Waktu |
|---|---|
| Baca HDD, urut jalur | 78 ms (42,9 MB/dtk) |
| Baca HDD, acak | 90 ms |
| SHA-1 | 5,5 ms |
| Dekode draft (rata2) | 101 ms; JPEG penuh 330 ms vs draft 169 ms (median, n=40) |
| Thumbnail 1024 + 256 | 50 ms |
| **Total** | **0,235 dtk/foto = 1,42 jam (1 proses)** |

HEIC 600 ms (n=1, hanya 110 file). **Temuan:** HDD bukan pembatas utama (baca ±28 menit total); dekode CPU yang dominan, jadi pekerja paralel berguna.
Satu file `.JPG` di contoh tidak bisa dibaca: pemindai harus mencatat dan melanjutkan.

## Deteksi (`model.py`, 40 foto, sisi panjang 1280, 4 thread)

| Model | Kanvas | ms/foto | Wajah ditemukan |
|---|---|---|---|
| 2.5G | 640 | 85 | 71 |
| 2.5G | 1280 | 303 | 71 |
| 10G | 640 | 226 | 69 |
| 10G | 1280 | 935 | 75 |

Jumlah wajah bukan ukuran benar/salah; contoh terlalu kecil untuk membedakan detektor.

## Embedding (`model.py`, ms/wajah, 60 wajah)

| Model | Ukuran | 1 thread | 2 thread | 4 thread |
|---|---|---|---|---|
| MobileFaceNet | 14 MB | 18 | 13 | 13 |
| R50 w600k | 174 MB | 387 | 234 | **164** |
| R100 glintr100 | 261 MB | 2.147 | 1.264 | **884** |

**R100 5,4x lebih mahal daripada R50**, bukan 2x seperti perkiraan rancangan.

## Waktu tahap B penuh (dihitung: 21.775 foto x 1,88 wajah/foto = ±40.900 wajah, CPU saja)

| Kombinasi | dtk/foto | Total |
|---|---|---|
| 10G@640 + R50 | 0,53 | **3,2 jam** |
| 10G@640 + R100 | 1,89 | 11,4 jam |
| 10G@1280 + R50 | 1,24 | 7,5 jam |
| 2.5G@640 + R50 | 0,39 | 2,4 jam |
| 2.5G@640 + MobileFaceNet | 0,11 | 0,7 jam |

## Cek pipa wajah (`cek_pipa.py`, 24 wajah, skala 100 % vs 70 %)

| Model | Wajah sama, median (min) | Wajah lain, median (p99) |
|---|---|---|
| MobileFaceNet | 0,993 (0,908) | 0,095 (0,438) |
| R50 | 0,992 (0,866) | 0,069 (0,429) |
| R100 | 0,993 (0,906) | 0,078 (0,364) |

Membuktikan deteksi, penyejajaran, dan embedding terpasang benar. **Bukan ukuran akurasi** membedakan orang.

## Grid QML (`ui_grid.py`, 20.000 thumbnail sintetis 256 px, 1280x800, D3D11 di HD 520, jam dinding)

| Fase | fps | median | p95 | p99 | RAM |
|---|---|---|---|---|---|
| Diam | 59,9 | 16 ms | 26 ms | 29 ms | 143 MB |
| Gulir 2.000 px/dtk | 60,0 | 17 ms | 22 ms | 29 ms | 191 MB |
| Scrub 30.000 px/dtk | 60,0 | 16 ms | 20 ms | 21 ms | 165 MB |
| Mendarat | 60,3 | 16 ms | 27 ms | 31 ms | 190 MB |

Lolos: Qt Quick cukup untuk grid. **Belum diuji:** baris rata (justified) dan thumbnail foto asli.

## Belum terukur

Akurasi membedakan orang (`dev/eval/pasangan.py`) menunggu set emas di `dev/eval/gold/<nama>/`. Pilihan model belum final.

# Hasil ukur Fase 1 (pustaka nyata, 8 November 2026)

| Ukuran | Hasil | Target |
|---|---|---|
| Pindai pertama 21.775 foto, 3 pekerja, HDD USB | 1.990 dtk (33 menit), 21.692 ok, 83 tak terbaca | - |
| Pindai ulang tanpa perubahan | 1 dtk (telusur 0,14 dtk bila cache hangat) | < 1 dtk: tercapai |
| Gulir 2.000 px/dtk, galeri asli | 59,9 fps, p95 22 ms, p99 31 ms | 60 fps: tercapai |
| Scrub 30.000 px/dtk | 58,0 fps, p95 28 ms, p99 47 ms | - |
| RAM saat gulir | 401 MB (puncak 403) | < 500 MB: tercapai |
| Buka aplikasi sampai frame pertama | 1,9 dtk (impor 0,6; QML+DB 1,0) | < 1 dtk: **belum** |
| `muatUlang` selama memindai | 0,25 dtk, tiap 4 dtk di benang UI | - |

83 file tak terbaca: 79 JPEG tidak dikenali Pillow, 3 OSError, 1 SyntaxError (2 PNG, 2 WebP termasuk di dalamnya). Tidak ada tanggal EXIF yang di luar akal pada pustaka ini.
Drive tercabut diuji dengan pustaka sintetis (folder dipindah), bukan mencabut E: sungguhan.


# Hasil ukur Fase 2 (pustaka nyata, 8 November 2026)

Model sementara: SCRFD-10G kanvas 640 + R50, 4 thread, 1 proses pekerja prioritas rendah.

| Ukuran | Hasil |
|---|---|
| 500 foto terbaru | 398 dtk (0,80 dtk/foto), 1.246 wajah (2,5 per foto), 0 gagal |
| 150 foto berikutnya, sambil galeri digulir | 155 dtk, 427 wajah, 0 gagal |
| Perkiraan seluruh pustaka (21.692 foto) | **±4,8 jam**, lebih lama dari perkiraan 3,2 jam: foto terbaru memuat lebih banyak wajah dan sebagian butuh baca foto asli |
| Wajah di bawah 40 px | 15 % |
| 164 dari 500 foto tanpa wajah | 33 % |

Galeri selama wajah berjalan, dibandingkan tanpa beban:

| | Tanpa beban | Saat wajah berjalan |
|---|---|---|
| Gulir | 59,7 fps, p99 34 ms | 60,0 fps, p99 23 ms |
| Scrub | 55,1 fps, p99 63 ms | 56,5 fps, p99 50 ms |
| RAM | 415 MB | 415 MB |

Pekerjaan wajah tidak menurunkan kelancaran karena berjalan di prioritas rendah. Satu pengukuran sebelumnya tidak sah (jendela tidak menggambar sama sekali, sebabnya tidak diketahui) dan dibuang.
Baru 650 dari 21.692 foto yang diproses. Akurasi belum terukur: menunggu set emas.

# Hasil Fase 3 (8 November 2026)

Pengelompokan pada 1.917 wajah nyata (salinan database): 0,2 detik, 82 kelompok, 1.339 wajah tertugaskan (70 %), 578 belum yakin.
Hanya kelompok berisi minimal 3 foto yang tampil; ini sengaja, v1 menghasilkan 721 orang untuk 5.155 wajah.
**Ketepatan belum terukur.** Ambang di `core/kelompok.py` belum dikalibrasi; menunggu set emas.
Target menamai 100 kelompok dalam 10 menit belum diukur, karena harus dicoba pemilik.

# Hasil Fase 4 (8 November 2026)

| Ukuran | Hasil | Target |
|---|---|---|
| Cari wajah pada data nyata (1.917 wajah), termasuk rincian dari SQLite | median 23,6 ms, maks 83 ms | < 100 ms: tercapai |
| Peringkat 45.000 wajah sintetis (matmul saja) | median 3,8 ms | - |
| Bangun indeks | 22 ms (1.917 wajah) | - |
| Saran teks | 83 ms bila dihitung ulang; kini hitungan folder disimpan dan hanya dihitung ulang saat foto berubah | - |

Syarat "foto contoh menemukan orang yang benar pada set emas" belum bisa diuji: set emas belum ada.
Rincian SQL pada pustaka penuh (±40.900 wajah) belum diukur; baru matmul-nya.


# Perbaikan pemilahan wajah (13 November 2026)

Diukur pada pustaka pemilik lewat salinan database; database asli hanya dibaca. Alat ukur: `dev/eval/tanpa_label.py`.
"Beda orang" = dua wajah dalam satu foto. "Sama orang" = wajah di posisi sama pada dua foto beruntun (pasangan mudah, jadi batas atas).

## Temuan: titik wajah kasar merusak embedding

Deteksi berjalan di kanvas 640 pada pratinjau 1024, sedangkan 93 % wajah di pustaka ini lebih kecil dari 112 px di pratinjau (median 34 px, jadi ±21 px saat dideteksi). Lima titiknya meleset, potongan wajah miring, dan orang berbeda tampak mirip.

Perbaikan: tiap wajah dideteksi ulang pada potongan 2,2 x lebar wajah dari sumber terbaiknya (kanvas 192), lalu titik itulah yang dipakai memotong. Titik bergeser median 6 % lebar wajah (p90 13 %); 2,7 % wajah tidak ketemu lagi dan memakai titik lama.

| | Sebelum | Sesudah |
|---|---|---|
| Wajah / foto yang diukur | 1.917 / 528 | 1.656 / 452 |
| Beda orang, median | 0,336 | 0,187 |
| Beda orang, p99 | 0,781 | 0,470 |
| Beda orang di atas ambang 0,50 | 18,4 % | 0,57 % |
| Sama orang di atas p99 beda-orang | 26 % (n=19) | 80 % (n=81) |
| d' | 1,57 | 2,83 |
| Wajah tertugaskan ke kelompok | 70 % | 77 % |
| Wajah ke pusat kelompoknya, median | 0,662 | 0,743 |
| Pasangan kelompok yang pusatnya mirip >= 0,5 | 417 | 15 |

Biaya: ±29 ms per wajah, kira-kira +10 % waktu per foto. 600 foto terukur 1,34 dtk/foto, tetapi saat itu uji lain ikut berjalan, jadi angka itu bukan patokan. Waktu seluruh pustaka belum diukur ulang.
**Belum terukur:** ketepatan kelompok terhadap label sebenarnya. Set emas tetap satu-satunya cara untuk itu.

## Model pengenal, pada potongan yang sudah dihaluskan (731 wajah, 2.196 pasangan beda, 34 pasangan sama)

| Model | ms/wajah | Beda p99 | Sama > p99 beda | d' |
|---|---|---|---|---|
| MobileFaceNet | 13 | 0,648 | 68 % | 2,19 |
| **R50 w600k (dipakai)** | **159** | **0,558** | **79 %** | **2,98** |
| R50 + cermin | 317 | 0,579 | 79 % | 3,05 |
| R100 glint360k | 704 | 0,580 | 76 % | 3,03 |

R100 4,4x lebih lambat dan tidak lebih baik secara berarti; cermin 2x lebih lambat untuk selisih yang sama kecilnya. R50 tetap dipakai. 34 pasangan "sama" terlalu sedikit untuk membedakan R50 dan R100 dengan pasti; yang pasti hanya bahwa MobileFaceNet lebih buruk.

## Ambang gabung dari data sendiri

`kelompok.ambang_dari_data`: p99 kemiripan beda-orang + 0,02, dibatasi 0,50 sampai 0,65. Pada salinan: 0,50 setelah 600 foto, 0,53 setelah 750 foto.

## Folder foto yang dipindah

Drive pemilik disusun ulang (folder akar berganti nama, isi berpindah). Di salinan: 13.636 dari 21.692 foto ketemu di lokasi baru, 11.412 di antaranya berpindah jalur dan dikenali tanpa dibaca ulang (1 detik), 8.056 tidak ada lagi di folder itu, 117 file baru. Tanpa pindah-cepat, 11.412 file itu harus dibaca dan di-hash ulang dari HDD.

## Mengapa tidak ditulis ulang ke Rust

Waktu tahap wajah per foto (±2,5 wajah): baca foto asli ±0,24 dtk, deteksi ±0,25 dtk, embedding ±0,17 dtk per wajah, penghalusan ±0,03 dtk per wajah. Deteksi dan embedding berjalan di ONNX Runtime (C++), dekode JPEG di libjpeg (C). Python hanya merangkai. Rust akan memanggil pustaka yang sama, jadi waktunya tidak berubah.

## Pengenalan wajah di kartu grafis (13 November 2026)

Yang mempercepat bukan bahasa, tetapi tempat hitungnya: OpenVINO di Intel HD 520, dengan ONNX Runtime di prosesor sebagai cadangan (`faces.pilih_alat`).

Per inferensi (`mesin_hitung.py`, ms):

| Mesin | deteksi 640 | deteksi 192 | 1 wajah | per wajah, kumpulan 8 |
|---|---|---|---|---|
| ONNX Runtime, 4 thread | 232 | 22 | 189 | 183 |
| OpenVINO prosesor | 306 | 27 | 187 | 183 |
| OpenVINO kartu grafis | 69 | 11 | 38 | 28 |

Embedding kartu grafis lawan ONNX Runtime: kosinus terendah 0,9988.

Per foto berwajah, rangkaian penuh `proses_foto` (60 foto acak dari pustaka, rata-rata 4,6 wajah/foto, prioritas proses rendah seperti pekerja sebenarnya, dua putaran berselang-seling di proses terpisah). Drive foto sedang tidak terpasang, jadi foto asli ditiru dengan memperbesar pratinjau; waktu baca HDD tidak termasuk.

| Mesin | ms/foto | deteksi + penghalusan | embedding | lain-lain |
|---|---|---|---|---|
| ONNX Runtime | 1.366 / 1.393 | 396 / 418 | 832 / 837 | 138 |
| OpenVINO kartu grafis | 397 / 420 | 143 / 164 | 151 | 105 |

Hasil: ±3,3x lebih cepat. Dua hal yang ternyata penting:

- Semua bentuk masukan dikompilasi saat pekerja dimuat (deteksi 640 dan 192, kumpulan wajah 1, 4, 8). Bila dibiarkan dikompilasi saat pertama dipakai, embedding 330 ms/foto dan penghalusan 163 ms/foto pada 80 foto pertama, karena kompilasi jatuh di tengah pekerjaan.
- Tiap ukuran kumpulan yang dikompilasi memakan RAM (kartu grafis terpadu memakai RAM sistem). RAM proses pekerja: kumpulan 1/2/4/8/16/32 = 1,8 GB, 1/4/8 = 0,8 GB, 1/8 = 0,6 GB, 8 saja = 0,5 GB. Kecepatan 1/4/8 sama dengan enam ukuran (496/509 lawan 506 ms/foto), jadi dipakai 1/4/8; lebih dari 8 wajah dipecah.
- Penghalusan dipindah ke prosesor sempat dicoba: lebih lambat (480 lawan 400 ms/foto), jadi tetap di kartu grafis.

Kompilasi pertama kali ±94 detik (sekali, disimpan di `data/cache_mesin`), sesudahnya ±6 detik per pekerja dimulai. Layar sumber menulis "Menyiapkan pengenal wajah" selama itu.

Kemasan (`dev/kemas`) membawa OpenVINO dengan plugin kartu grafis saja (plugin prosesor dan NPU, ±150 MB, ditinggal). Uji `Recognice.exe --uji` menulis `ok openvino-GPU`. Ukuran folder kemasan tanpa data: 520 MB.

Belum diukur: waktu nyata dengan foto asli dari HDD (drive tidak terpasang saat pengukuran).

## Galeri digulir (`galeri.py`, pustaka nyata 21.692 foto, 1168 px, HD 520)

Seret penggulir (30.000 px/dtk) tersendat parah: 1,4 sampai 1,9 fps, tiap bingkai ±0,5 detik. Penyebabnya: tiap lompatan mengganti ±37 dari 48 slot baris, dan tiap slot membangun ulang semua sel fotonya (±8 ms per slot). Dua perbaikan:

- Hanya baris dekat layar (layar ± 700 px) yang diisi; slot lain dibiarkan memegang baris lamanya selama baris itu masih sah di tata sekarang.
- Sel foto dipakai ulang: baris berganti isi hanya mengubah ikatan, sel tidak dibuat ulang.

| Fase | Sebelum | Sesudah |
|---|---|---|
| Gulir 2.000 px/dtk | 55-57 fps | 53-58 fps |
| Seret 30.000 px/dtk | 1,4-1,9 fps, median 470-600 ms | 39-47 fps, median 17-19 ms |

Saat pengenal wajah bekerja di kartu grafis (beban sintetis terus-menerus, 2,6 foto/dtk): gulir biasa 50-54 fps, seret 8-15 fps. Pengenal di prosesor: gulir 53 fps. Prioritas antrean kartu grafis rendah (`GPU_QUEUE_PRIORITY`, `GPU_QUEUE_THROTTLE`) dicoba berselang-seling dua kali: tidak ada beda, jadi tidak dipakai. Menjeda pengenal saat digulir tidak dipasang: pekerja memegang sampai 3 foto (±1,2 detik), jadi jedanya baru berlaku setelah seretan biasanya selesai.

## Buka aplikasi (`mulai_rinci.py`, pustaka nyata, jalan kedua dan seterusnya)

Bingkai pertama 2,2 sampai 3,0 detik: impor Qt ±0,4-0,7, impor aplikasi (numpy dan sejenisnya) ±0,6-1,0, membuat mesin QML ±0,8-1,0. Diubah: pohon folder (0,17 detik) baru dibaca saat halaman Folder dibuka, dan halaman selain Galeri baru dibuat saat pertama dikunjungi. Hasil terukur ±0,2 detik; pengukuran berisik karena prosesor sedang dipakai program lain (beban 16-56 %). Buka dingin setelah komputer baru dinyalakan belum diukur.
