# Desain Recognice

Meniru Microsoft Photos terbaru di Windows 11 sedekat mungkin, atas permintaan pemilik. Ukuran dan warna diukur dari tangkapan referensi. Audit ada di `docs/audit-ui-microsoft-photos.md`. Token ada di `app/ui/qml/theme/Theme.qml`; komponen di `app/ui/qml/components/`.

## Kerangka

Bilah judul buatan sendiri setinggi 48 px: ikon dan nama di kiri, kotak cari pil di tengah jendela, tombol jendela di kanan. Bagian kosongnya tetap milik Windows: `ui/bridge/bingkai.py` menjawab WM_NCHITTEST sehingga geser, ubah ukuran, Aero Snap, bayangan, sudut bulat, dan menu Snap Layouts pada tombol perbesar berasal dari Windows.

Rel ikon 48 px di kiri, lima tujuan di atas dan Pengaturan di dasar. Baris kepala 72 px: judul 42 bold, pil tanggal, lalu Filter, tombol ukuran bulat, dan Tambah folder. Halaman awal Galeri; bisa diganti Folder di Pengaturan.

## Warna

| Token | Gelap | Terang | Peran |
|---|---|---|---|
| `kanvas` | `#0a0a0a` | `#f3f3f3` | jendela dan area foto |
| `permukaan` | `#1f1f1f` | `#fbfbfb` | panel dan kartu |
| `isi` | `#1f1f1f` | `#ffffff` | pil dan kotak cari |
| `sorot` / `sorotKuat` | `#2c2c2c` / `#363636` | `#e9e9e9` / `#dedede` | disorot, ditekan, tempat gambar |
| `garis` | `#333333` | `#e0e0e0` | garis kontrol |
| `teksJudul` | `#ffffff` | `#111111` | hanya judul halaman |
| `teks` / `teks2` / `teks3` | `#e6e6e6` / `#a6a6a6` / `#999999` | `#1a1a1a` / `#5c5c5c` / `#666666` | kontrol dan isi / label, nama, teks pengisi / linimasa dan nama aplikasi |
| `aksen` | Light 2 Windows | Dark 1 Windows | garis, penanda, teks aktif |
| `aksenIsi` | Dark 1 Windows | Dark 1 Windows | tombol utama dan pilihan terisi |
| `layar` / `layarPanel` | `#1a1e2a` / `#2b2d30` | sama | penampil foto, selalu gelap |

Aksen dibaca dari `AccentPalette` Windows. Aksen yang kontrasnya kurang dari 3:1 terhadap kanvas diganti biru bawaan. Warna Qt beralfa ditulis `#AARRGGBB`.

## Huruf dan ikon

Segoe UI Variable (Text untuk isi, Display untuk judul) dengan perenderan asli. Peran di `Teks.qml`, diukur dari tinggi huruf referensi: judul 42/54 bold, besar 20/28, sedang 15/20 (pil tanggal), teks 13/18, kecil 11/14. Putih murni hanya untuk judul halaman; kontrol memakai `teks`, label memakai `teks2`. Ikon dari Segoe Fluent Icons, skala abu, 14 px; ikon rel 15 px.

## Bentuk

Foto sudut 10, panel 12, tombol berteks dan pilihan berbentuk pil, kontrol 36. Sudut foto ditutup `SudutFoto` (satu tekstur untuk semua ubin) karena topeng per foto berat di HD 520; kanvas harus warna padat agar cara ini benar.

## Galeri

Di puncak Galeri tanpa saringan ada deret lima kartu: Terbaru, Hari ini dulu (atau Bulan ini dulu), dua orang terbanyak, dan folder terbesar. Deret ikut tergulir. Di bawahnya satu dinding foto tanpa kepala tanggal, celah 16, tinggi baris 120 / 170 / 260. Tanggal foto teratas ada di pil. Linimasa di tepi paling kanan, di luar panel Filter: chevron, label tahun, garis tiap bulan, penanda aksen.

Panel Filter 288 px memperhalus tampilan aktif: tahun, orang (semua atau salah satu), sumber, orientasi, resolusi. Panel kosong lagi saat berpindah tampilan.

## Folder

Kartu folder dengan kolase tiga foto terbaru bila kartu cukup lebar, jumlah foto dan subfolder di kaki kartu. Sedikit folder tetap memenuhi baris (paling sedikit tiga kolom). Di bawahnya, dalam satu gulir, dinding sampai 60 foto terbaru dari folder yang sedang dibuka, seluruhnya dari thumbnail lokal; baris terakhir yang tidak penuh dibuang. Foto yang dibuka dari dinding kembali ke Folder saat penampil ditutup.

## Penampil

Bilah judul penampil: kembali di kiri, nama berkas di tengah, alat dan tombol jendela di kanan. Foto di panggung dengan jajaran foto mengambang di bawahnya. Bilah status: format dan dimensi di kiri, pas layar, persen, dan penggeser zoom di kanan. Panel mengambang 288 px bertab Info dan Orang, terbuka bawaan bila lebar jendela paling sedikit 960 px. Foto asli dibaca hanya saat diperbesar.

## Gerak

Foto memekar dari ubin 220 ms dan kembali 167 ms. Panel Filter 167 ms, thumbnail memudar 167 ms, warna tombol 83 ms. Lebar galeri berubah sekali saat panel dibuka, karena menyusun ulang tiap bingkai berat.

## Lebar sempit

Minimum 720 x 480. Di bawah 1050 px lebar isi, pil tanggal dan Tambah folder disembunyikan. Penampil menyembunyikan panel di bawah 960 px dan jajaran foto di bawah tinggi 560 px.

## Bahasa

Bahasa sehari-hari, bukan istilah teknis: "Lokasi foto" (bukan sumber), "Periksa foto baru" (bukan pindai), "Beri nama" (bukan tinjau kelompok), "Siapa ini?" untuk orang tanpa nama, "ada masalah" (bukan galat). Pesan menyebut apa yang terjadi dan apa yang bisa dilakukan. Orang tanpa nama yang diklik langsung membuka halaman Beri nama.

## Aksesibilitas

Tombol, butir rel, pilihan, sakelar, dan kisi (foto, folder, orang) bisa difokus Tab dengan cincin fokus; di dalam kisi panah berpindah dan Enter membuka. Ctrl+F membuka pencarian. Kotak cari disembunyikan saat Tinjau karena alur itu sepenuhnya keyboard. Penampil penuh keyboard: panah, Esc, I, F, +, -, 0.
