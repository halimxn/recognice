# Audit UI/UX terhadap Microsoft Photos

Tanggal 9 November 2026. Pembanding: lima tangkapan Microsoft Photos dari pemilik (Galeri dengan panel Filter, penyunting, dan penampil dengan panel Info). Bukti tampilan lama dan baru ada di `dev/uji/foto/`, seluruhnya foto sintetis.

Keputusan pemilik: warna aksen dan huruf mengikuti Windows. Setelah revisi pertama dinilai belum mirip, pemilik meminta tampilan semirip mungkin; lihat bagian Revisi kedua.

## Temuan pada tampilan lama

Tingkat: **T** tinggi, **S** sedang, **R** rendah.

| # | Tingkat | Bagian | Masalah | Di Microsoft Photos | Perbaikan |
|---|---|---|---|---|---|
| 1 | T | Kerangka | Rel berlabel 208 px memakan 15% layar 1366 px | Rel ikon sempit | Rel ikon 56 px dengan petunjuk saat disorot |
| 2 | T | Kerangka | Bilah judul, rel, dan isi berbeda warna, terasa seperti halaman web dalam jendela | Satu permukaan menyatu | Bilah judul Windows, rel, dan kanvas satu warna |
| 3 | T | Pencarian | Cari adalah halaman terpisah; butuh pindah halaman lalu menekan "Lihat foto" | Kotak cari selalu ada | Kotak cari tetap di tengah semua halaman; memilih saran langsung membuka foto; Ctrl+F |
| 4 | T | Galeri | Tidak ada cara menyaring selain orang lewat halaman Cari | Panel Filter dengan wajah, sumber, orientasi, resolusi | Panel Filter 300 px, termasuk pilihan "salah satu orang" |
| 5 | T | Penampil | Latar hitam dengan tombol lepas, tanpa nama foto atau bilah alat | Bilah alat, nama berkas, jajaran foto, bilah zoom | Bilah alat mengambang, nama dan tanggal, jajaran dalam baki, penggeser zoom dengan persen sebenarnya |
| 6 | T | Penampil | Rincian hanya daftar teks; wajah di foto tidak terlihat | Panel Info berikon dengan kolom | Panel Info berikon; bagian "Orang di foto ini" membuka orangnya |
| 7 | S | Galeri | Kepala per hari memecah dinding foto | Kelompok per bulan dengan jumlah | Kepala per bulan dan jumlah foto; rincian hari ada di Info |
| 8 | S | Galeri | Foto bersudut tajam dengan celah 4 px | Sudut membulat, celah lapang | Sudut 6, celah 6 |
| 9 | S | Galeri | Tidak tahu sedang di bulan apa saat menggulir | Pil tanggal di samping judul | Pil bulan yang mengikuti guliran |
| 10 | S | Linimasa | Hanya label tahun | Tahun dengan garis-garis waktu | Label tahun, garis tiap bulan, penanda aksen |
| 11 | S | Ukuran foto | Tombol tambah dan kurang, ukuran saat ini tidak terlihat | Tiga pilihan tampilan | Tiga tombol ukuran, yang aktif menyala |
| 12 | S | Ikon | SVG dirender per ikon saat mulai, gayanya bukan gaya Windows | Segoe Fluent Icons | Fon ikon sistem, tanpa berkas gambar |
| 13 | S | Huruf | Inter dibundel, teks kurang tajam pada 100% | Segoe UI Variable | Huruf sistem dengan perenderan asli; 880 KB fon dihapus |
| 14 | S | Sumber, Pengaturan | Teks dan tombol lepas di kanvas | Kartu gaya Pengaturan Windows | Kartu baris: ikon, judul, keterangan, kontrol di kanan; sakelar untuk baterai |
| 15 | S | Folder | Ubin polos, tanpa jejak lokasi | Kartu dengan sampul dan keterangan | Kartu bersudut, jejak folder yang bisa diklik |
| 16 | R | Interaksi | Kursor tangan di semua tombol, kebiasaan web | Kursor panah | Kursor panah; tangan hanya untuk menggeser foto |
| 17 | R | Petunjuk | Tombol ikon tanpa nama saat disorot | Tooltip | Satu petunjuk bersama untuk seluruh aplikasi |
| 18 | R | Status | Status pindai hanya di rel lebar | Tidak ada pembanding | Garis progres 2 px di atas isi dan titik pada ikon Sumber |
| 19 | R | Penampil | Foto muncul begitu saja | Transisi dari ubin | Foto memekar dari ubinnya 220 ms |

## Revisi kedua

Revisi pertama meniru susunan tetapi tidak meniru ukurannya. Setelah tangkapan referensi diukur:

| Unsur | Revisi pertama | Referensi dan sekarang |
|---|---|---|
| Kanvas | `#202020` | `#0a0a0a` |
| Panel | `#2b2b2b` | `#1f1f1f` |
| Tombol utama | biru muda | biru pekat aksen Windows, teks putih |
| Judul halaman | 28 px | 40 px |
| Celah foto | 6 px | 16 px |
| Sudut foto | 6 px | 10 px |
| Tanggal | kepala per bulan | satu dinding foto, tanggal di pil |
| Kotak cari | baris kepala | bilah judul, tengah jendela |
| Linimasa | antara foto dan panel | tepi paling kanan, dengan chevron |
| Tombol ukuran | tiga tombol | satu tombol bulat dengan menu |
| Penampil | kepala terpisah, alat di tengah | menyatu dengan bilah judul, bilah status bawah, panel mengambang bertab |
| Halaman awal | Folder | Galeri; Folder bisa dipilih di Pengaturan |

## Revisi ketiga

Pemilik menilai ukuran dan warna huruf belum tepat dan tampilan terasa sepi. Tinggi huruf dan warna teks referensi diukur pada lebar jendela yang sama.

| Unsur | Sebelumnya | Sekarang |
|---|---|---|
| Teks kontrol | 14 px, putih | 13 px, `#e6e6e6` |
| Label, nama, pengisi | 12 px, `#b8b8b8` | 11 px, `#a6a6a6` |
| Linimasa, nama aplikasi | `#b8b8b8` | `#999999` |
| Pil tanggal | 14 px | 15 px |
| Judul | 40 px semibold | 42 px bold, satu-satunya putih murni |
| Ikon rel | 18 px, putih | 15 px, abu; aktif beraksen |
| Puncak Galeri | langsung dinding foto | deret lima kartu dari data sendiri |
| Rel | tujuan terpisah atas dan bawah | lima tujuan rapat di atas |
| Cari dengan foto | area kosong | daftar orang yang sudah dikenali |

Halaman Folder juga dinilai masih sepi: kartunya kini berkolase dan mengisi baris, dan di bawahnya ada dinding foto terbaru dari folder yang dibuka.

## Bug yang ikut ditemukan

"Lihat semua foto" pada akar sebuah sumber selalu kosong, karena saringan folder mencari awalan `/`. Sudah diperbaiki dan punya uji.

## Sengaja tidak ditiru

| Di Microsoft Photos | Alasan |
|---|---|
| Crop, Enhance, Relight, Save | Foto asli hanya dibaca, itu aturan utama aplikasi ini |
| OneDrive, iCloud, unggah | Tidak ada jaringan saat aplikasi berjalan |
| Video, Favorit, Sampah | Fitur itu belum ada; tombol kosong hanya menipu |
| Mica dan Acrylic | Sudut foto digambar di atas warna padat; kanvas memakai warna terukur dari referensi |
| Peta lokasi, rincian kamera | Data itu belum disimpan saat memindai |

## Yang berubah dari fitur lama

Chip gabungan di halaman Cari diganti panel Filter. Orang, tahun, sumber, dan folder tetap bisa digabung, tetapi panel hanya punya tahun, jadi gabungan **bulan + folder** tidak bisa lagi dibuat.

## Belum diuji

- Rasa di laptop asli dengan 21.692 foto dan HDD eksternal. Semua tangkapan memakai 420 foto sintetis.
- Windows 10: huruf dan ikon punya cadangan di kode, tetapi tidak dicoba.
- Layar berskala di atas 100%: sudut foto digambar dari tekstur 1x dan mungkin sedikit kurang tajam.
- Pembaca layar.
