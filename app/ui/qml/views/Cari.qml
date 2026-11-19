import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: akar
    objectName: "cariHalaman"
    signal lihatFoto(var saringan)
    signal bukaOrang(int id)
    signal bukaFotoHasil(var saringan, int photoId)

    function angka(n) { return n.toLocaleString(Qt.locale("id_ID"), "f", 0) }

    FileDialog {
        id: pilihContoh
        title: qsTr("Pilih foto contoh")
        nameFilters: [qsTr("Foto (*.jpg *.jpeg *.png *.webp *.heic *.heif)")]
        onAccepted: cari.contohUrl(selectedFile.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        anchors.bottomMargin: Theme.j16
        spacing: Theme.j12

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiKepala
            Teks {
                anchors.verticalCenter: parent.verticalCenter
                peran: "judul"
                width: parent.width - Theme.j40 * 5
                text: qsTr("Cari dengan foto")
            }
        }

        // Zona seret; berubah menjadi ringkas setelah ada hasil
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: cari.hasil.status === "hasil" ? Theme.zonaRingkas : Theme.zonaSeret
            radius: Theme.sudut
            color: seret.containsDrag ? Theme.sorot : Theme.permukaan
            border.width: 1
            border.color: seret.containsDrag ? Theme.aksen : Theme.garis

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j24
                anchors.rightMargin: Theme.j24
                spacing: Theme.j16
                Ikon {
                    visible: !cari.hasil.kueri && cari.hasil.status !== "pilih"
                    nama: "cariFoto"
                    ukuran: Theme.j32
                    warna: Theme.teks2
                }
                Image {
                    visible: !!cari.hasil.kueri
                    source: cari.hasil.kueri || ""
                    Layout.preferredWidth: Theme.j40
                    Layout.preferredHeight: Theme.j40
                    sourceSize: Qt.size(96, 96)
                    asynchronous: true
                }
                Teks {
                    Layout.fillWidth: cari.hasil.status !== "pilih"
                    color: cari.hasil.status === "pesan" ? Theme.bahaya : Theme.teks
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    text: cari.hasil.status === "memproses" ? qsTr("Mencari wajah…")
                        : cari.hasil.status === "pesan" ? cari.hasil.pesan
                        : cari.hasil.status === "pilih" ? qsTr("Ada beberapa wajah di foto ini. Klik wajah yang dicari.")
                        : cari.hasil.status === "hasil" ? qsTr("Foto dengan wajah mirip. Tingkat kemiripan hanya perkiraan.")
                        : !cari.bisaContoh ? qsTr("Pencarian pakai foto belum bisa dipakai karena berkas pengenal wajah tidak ada.")
                        : qsTr("Seret foto seseorang ke sini. Recognice akan mencari foto lain yang memuat orang itu.")
                }
                // Foto rombongan bisa berisi puluhan wajah: digulir mendatar
                ListView {
                    visible: cari.hasil.status === "pilih"
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.wajahKecil
                    orientation: ListView.Horizontal
                    spacing: Theme.j8
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: cari.hasil.pilihan || []
                    delegate: Image {
                        required property var modelData
                        width: Theme.wajahKecil; height: Theme.wajahKecil
                        sourceSize: Qt.size(192, 192)
                        asynchronous: true
                        source: modelData.url
                        MouseArea { anchors.fill: parent; onClicked: cari.pilihWajah(parent.modelData.i) }
                    }
                }
                Tombol { teks: qsTr("Pilih foto"); jenis: cari.hasil.status === "hasil" ? "polos" : "utama"; mati: !cari.bisaContoh; onDiklik: pilihContoh.open() }
            }
            DropArea {
                id: seret
                anchors.fill: parent
                onDropped: (d) => { if (d.hasUrls && cari.bisaContoh) cari.contohUrl(d.urls[0].toString()) }
            }
        }

        RowLayout {
            visible: cari.hasil.status === "hasil" && cari.hasil.orang.length > 0
            Layout.fillWidth: true
            spacing: Theme.j16
            Repeater {
                model: cari.hasil.orang || []
                delegate: Item {
                    required property var modelData
                    Layout.preferredWidth: Theme.lebarOrangHasil
                    Layout.preferredHeight: Theme.tinggiOrangHasil
                    Column {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: Theme.j4
                        Image { anchors.horizontalCenter: parent.horizontalCenter; width: Theme.wajahKecil; height: Theme.wajahKecil; sourceSize: Qt.size(192, 192); asynchronous: true; source: parent.parent.modelData.url }
                        Teks { width: Theme.lebarOrangHasil; horizontalAlignment: Text.AlignHCenter; font.weight: Font.DemiBold; text: parent.parent.modelData.nama || qsTr("Siapa ini?") }
                        Teks { width: Theme.lebarOrangHasil; horizontalAlignment: Text.AlignHCenter; peran: "kecil"; color: Theme.teks2; text: parent.parent.modelData.pita }
                    }
                    MouseArea { anchors.fill: parent; onClicked: akar.bukaOrang(parent.modelData.id) }
                }
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            visible: cari.hasil.status === "hasil"
            Layout.fillWidth: true
            Teks {
                Layout.fillWidth: true
                font.weight: Font.DemiBold
                text: (cari.hasil.wajah || []).length ? qsTr("%1 wajah mirip").arg(akar.angka(cari.hasil.wajah.length)) : qsTr("Tidak ada wajah yang cukup mirip.")
            }
            Tombol {
                visible: (cari.hasil.wajah || []).length > 0
                teks: qsTr("Lihat fotonya")
                onDiklik: akar.lihatFoto(cari.saringanHasil())
            }
        }

        GridView {
            id: kisi
            visible: cari.hasil.status === "hasil"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: cari.hasil.wajah || []
            cellWidth: Theme.selHasilLebar
            cellHeight: Theme.selHasilTinggi
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Gulir {}
            cacheBuffer: 300
            delegate: Item {
                id: sel
                required property var modelData
                width: kisi.cellWidth
                height: kisi.cellHeight
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.j4
                    Image { anchors.horizontalCenter: parent.horizontalCenter; width: Theme.wajahHasil; height: Theme.wajahHasil; sourceSize: Qt.size(192, 192); asynchronous: true; source: sel.modelData.url }
                    Teks { width: Theme.lebarOrangHasil; horizontalAlignment: Text.AlignHCenter; peran: "kecil"; color: Theme.teks2; text: sel.modelData.pita }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: akar.bukaFotoHasil(cari.saringanHasil(), sel.modelData.photoId)
                }
            }
        }

        // Sebelum ada hasil: orang yang sudah dikenal, satu klik ke fotonya
        Teks {
            visible: cari.hasil.status !== "hasil" && orang.daftar.length > 0
            Layout.topMargin: Theme.j12
            color: Theme.teks2
            text: qsTr("Orang yang sudah dikenali")
        }
        GridView {
            visible: cari.hasil.status !== "hasil" && orang.daftar.length > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: orang.daftar
            cellWidth: Theme.selHasilLebar + Theme.j8
            cellHeight: Theme.selHasilTinggi
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Gulir {}
            delegate: Item {
                required property var modelData
                width: GridView.view.cellWidth
                height: GridView.view.cellHeight
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.j4
                    Image { anchors.horizontalCenter: parent.horizontalCenter; width: Theme.wajahHasil; height: Theme.wajahHasil; sourceSize: Qt.size(192, 192); asynchronous: true; source: parent.parent.modelData.url }
                    Teks { width: Theme.lebarOrangHasil; horizontalAlignment: Text.AlignHCenter; peran: "kecil"; color: Theme.teks2; text: parent.parent.modelData.nama || qsTr("Siapa ini?") }
                }
                MouseArea { anchors.fill: parent; onClicked: akar.bukaOrang(parent.modelData.id) }
            }
        }
        Item { visible: cari.hasil.status !== "hasil" && orang.daftar.length === 0; Layout.fillHeight: true }
    }
}
