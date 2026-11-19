import QtQuick
import "../theme"

// Ikon bawaan Windows dari fon sistem: sama dengan aplikasi Windows lain, tanpa berkas gambar
Text {
    property string nama: ""
    property color warna: Theme.teks
    property int ukuran: 14

    readonly property var kode: ({
        "folder": 0xE8B7, "galeri": 0xECA5, "orang": 0xE716, "wajah": 0xE8D4, "cari": 0xE721, "cariFoto": 0xE773,
        "sumber": 0xEDA2, "atur": 0xE713, "tambah": 0xE710, "kurang": 0xE738, "tutup": 0xE711, "kiri": 0xE76B,
        "kanan": 0xE76C, "kembali": 0xE72B, "info": 0xE946, "ulang": 0xE72C, "jeda": 0xE769, "putar": 0xE768,
        "buka": 0xE838, "hapus": 0xE74D, "filter": 0xE71C, "perbesar": 0xE8A3, "perkecil": 0xE71F, "pas": 0xE9A6,
        "salin": 0xE8C8, "kalender": 0xE787, "gambar": 0xE8B9, "berkas": 0xE8A5, "centang": 0xE73E, "besar": 0xE739,
        "sedang": 0xF0E2, "kecil": 0xE80A, "tampil": 0xE8B3, "bawah": 0xE70D, "atas": 0xE70E, "minimal": 0xE921, "maksimal": 0xE922,
        "pulihkan": 0xE923, "tutupJendela": 0xE8BB, "ukuran": 0xE9E9
    })

    width: ukuran
    height: ukuran
    text: kode[nama] ? String.fromCodePoint(kode[nama]) : ""
    color: warna
    font.family: Theme.hurufIkon
    font.pixelSize: ukuran
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    renderType: Text.QtRendering  // skala abu seperti ikon Windows; ClearType memberi tepi berwarna
    Accessible.ignored: true
}
