import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

// Satu kotak cari untuk seluruh aplikasi: pilih saran, langsung ke fotonya
Item {
    id: akar
    objectName: "kotakCari"
    signal pilihOrang(int id)
    signal pilihSaringan(var saringan)
    signal cariFoto()

    readonly property bool terbuka: kolom.activeFocus
    property int pilih: -1
    readonly property var saran: {
        const s = cari.saran, h = []
        const angka = (n) => qsTr("%1 foto").arg(n.toLocaleString(Qt.locale("id_ID"), "f", 0))
        for (const o of s.orang) h.push({ judul: o.nama, info: angka(o.jumlah), url: o.url, ikon: "", aksi: () => akar.pilihOrang(o.id) })
        for (const t of s.tanggal) h.push({ judul: t.label, info: angka(t.jumlah), url: "", ikon: "kalender",
            aksi: () => akar.pilihSaringan({ tahun: t.tahun, bulan: t.bulan, label: t.label }) })
        for (const f of s.folder) h.push({ judul: f.rel, info: angka(f.jumlah), url: "", ikon: "folder",
            aksi: () => akar.pilihSaringan({ folder: { source: f.source, rel: f.rel }, label: f.rel.split("/").pop() }) })
        return h
    }

    function fokus() { kolom.forceActiveFocus(); kolom.selectAll() }
    property alias teksUji: kolom.text
    function tutup() { kolom.text = ""; cari.ketik(""); pilih = -1; kolom.focus = false; jangkar.forceActiveFocus() }
    function jalankan(i) { const b = saran[i]; if (b) { tutup(); b.aksi() } }

    implicitHeight: Theme.tinggiCari
    Item { id: jangkar; focus: false }

    TextField {
        id: kolom
        anchors.fill: parent
        color: Theme.teksCangkang
        placeholderText: qsTr("Cari orang, folder, atau tanggal")
        placeholderTextColor: Theme.teksCangkang2
        selectionColor: Theme.aksen
        selectedTextColor: Theme.padaAksen
        font.family: Theme.huruf
        font.pixelSize: Theme.ukTeks
        renderType: Text.NativeRendering
        verticalAlignment: Text.AlignVCenter
        leftPadding: Theme.j40
        rightPadding: Theme.j16
        Accessible.name: qsTr("Cari")
        background: Rectangle {
            radius: height / 2
            color: kolom.hovered && !kolom.activeFocus ? Theme.cangkangSorot : Theme.cangkangIsi
            border.width: kolom.activeFocus ? Theme.j2 : 0
            border.color: Theme.aksen
        }
        onTextEdited: { cari.ketik(text); akar.pilih = -1 }
        Keys.onDownPressed: akar.pilih = Math.min(akar.pilih + 1, akar.saran.length - 1)
        Keys.onUpPressed: akar.pilih = Math.max(akar.pilih - 1, -1)
        Keys.onReturnPressed: akar.jalankan(Math.max(akar.pilih, 0))
        Keys.onEnterPressed: akar.jalankan(Math.max(akar.pilih, 0))
        Keys.onEscapePressed: akar.tutup()
    }
    Ikon {
        nama: "cari"
        warna: Theme.teksCangkang2
        x: Theme.j16 - 2
        anchors.verticalCenter: parent.verticalCenter
    }

    Kartu {
        visible: akar.terbuka
        y: parent.height + Theme.j4
        width: parent.width
        height: isi.implicitHeight + Theme.j8

        ColumnLayout {
            id: isi
            anchors.fill: parent
            anchors.margins: Theme.j4
            spacing: 0

            Repeater {
                model: akar.saran
                delegate: Rectangle {
                    id: baris
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.j40
                    radius: Theme.sudutKontrol
                    color: akar.pilih === index ? Theme.sorotKuat : area.containsMouse ? Theme.sorot : "transparent"
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.j8
                        anchors.rightMargin: Theme.j12
                        spacing: Theme.j12
                        Image {
                            visible: baris.modelData.url !== ""
                            source: baris.modelData.url
                            sourceSize: Qt.size(64, 64)
                            asynchronous: true
                            Layout.preferredWidth: Theme.j32 - Theme.j4
                            Layout.preferredHeight: Theme.j32 - Theme.j4
                        }
                        Ikon { visible: baris.modelData.ikon !== ""; nama: baris.modelData.ikon; warna: Theme.teks2; Layout.preferredWidth: Theme.j32 - Theme.j4 }
                        Teks { text: baris.modelData.judul; Layout.fillWidth: true }
                        Teks { text: baris.modelData.info; color: Theme.teks2; peran: "kecil" }
                    }
                    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: akar.jalankan(baris.index) }
                }
            }

            Rectangle {
                visible: akar.saran.length > 0
                Layout.fillWidth: true
                Layout.topMargin: Theme.j4
                Layout.bottomMargin: Theme.j4
                height: 1
                color: Theme.garis
            }

            Teks {
                visible: kolom.text !== "" && akar.saran.length === 0
                Layout.margins: Theme.j8
                color: Theme.teks2
                text: qsTr("Tidak ada orang, folder, atau tanggal yang cocok.")
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.j40
                radius: Theme.sudutKontrol
                color: bawah.containsMouse ? Theme.sorot : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.j8
                    anchors.rightMargin: Theme.j12
                    spacing: Theme.j12
                    Ikon { nama: "cariFoto"; warna: Theme.teks2; Layout.preferredWidth: Theme.j32 - Theme.j4 }
                    Teks { text: qsTr("Cari pakai foto seseorang"); Layout.fillWidth: true }
                }
                MouseArea { id: bawah; anchors.fill: parent; hoverEnabled: true; onClicked: { akar.tutup(); akar.cariFoto() } }
            }
        }
    }
}
