import QtQuick
import QtQuick.Layouts
import "../theme"

ColumnLayout {
    id: akar
    property string ikon: "gambar"
    property string judul: ""
    property string keterangan: ""
    property string aksi: ""
    signal diklik()

    spacing: Theme.j8

    Ikon {
        nama: akar.ikon
        ukuran: Theme.j40
        warna: Theme.teks2
        Layout.alignment: Qt.AlignHCenter
        Layout.bottomMargin: Theme.j8
    }
    Teks { text: akar.judul; peran: "besar"; Layout.alignment: Qt.AlignHCenter }
    Teks {
        text: akar.keterangan
        color: Theme.teks2
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        Layout.maximumWidth: 420
        Layout.alignment: Qt.AlignHCenter
    }
    Tombol {
        visible: akar.aksi !== ""
        teks: akar.aksi
        ikon: "tambah"
        jenis: "utama"
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: Theme.j16
        onDiklik: akar.diklik()
    }
}
