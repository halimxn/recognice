import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: akar
    signal lihat(var saringan)
    signal tambahFolder()
    signal bukaFoto(var saringan, int photoId)
    signal semuaFoto()

    function angka(n) { return n.toLocaleString(Qt.locale("id_ID"), "f", 0) }
    onVisibleChanged: if (visible) folder.segarkan()  // juga saat halaman pertama dibuat: pohon folder dibaca di sini

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        spacing: 0
        visible: folder.anak.length > 0 || folder.dalam

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiKepala
            spacing: Theme.j12

            Tombol { visible: folder.dalam; jenis: "ikon"; ikon: "kembali"; petunjuk: qsTr("Kembali ke folder sebelumnya"); onDiklik: folder.naik() }
            ColumnLayout {
                visible: folder.dalam
                spacing: 0
                Row {
                    spacing: Theme.j4
                    Teks {
                        peran: "kecil"
                        color: Theme.teks2
                        text: qsTr("Folder")
                        MouseArea { anchors.fill: parent; onClicked: folder.keAkar() }
                    }
                    Repeater {
                        model: folder.jejak.slice(0, -1)
                        delegate: Row {
                            required property var modelData
                            spacing: Theme.j4
                            Ikon { nama: "kanan"; ukuran: Theme.j8; warna: Theme.teks2; anchors.verticalCenter: parent.verticalCenter }
                            Teks {
                                peran: "kecil"
                                color: Theme.teks2
                                text: parent.modelData.nama
                                MouseArea { anchors.fill: parent; onClicked: folder.masuk(parent.parent.modelData.source, parent.parent.modelData.rel) }
                            }
                        }
                    }
                }
                Teks { peran: "besar"; text: folder.judul; Layout.maximumWidth: Theme.lebarJudulMaks }
            }
            Teks { visible: !folder.dalam; peran: "judul"; text: qsTr("Folder") }
            Rectangle {
                Layout.preferredHeight: Theme.tinggiKontrol
                Layout.preferredWidth: jumlahFoto.implicitWidth + Theme.j32
                radius: height / 2
                color: Theme.isi
                Teks { id: jumlahFoto; anchors.centerIn: parent; color: Theme.padaIsi; text: qsTr("%1 foto").arg(akar.angka(folder.jumlah)) }
            }
            Item { Layout.fillWidth: true }
            Tombol { visible: folder.dalam; teks: qsTr("Lihat semua foto"); ikon: "galeri"; onDiklik: akar.lihat(folder.saringanIni()) }
            Tombol { visible: !folder.dalam; teks: qsTr("Tambah folder"); ikon: "tambah"; jenis: "utama"; onDiklik: akar.tambahFolder() }
        }

        GridView {
            id: kisi
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: -Theme.j8
            Layout.rightMargin: -Theme.j8
            clip: true
            model: folder.anak
            // Sedikit folder tetap memenuhi baris; paling sedikit tiga kolom agar kartu tidak raksasa
            readonly property int kolom: Math.max(1, Math.min(Math.floor(width / Theme.lebarSelFolder), Math.max(3, folder.anak.length)))
            // Bilangan bulat: tepi pecahan membuat foto mengintip di balik sudut
            cellWidth: width > 0 ? Math.floor(width / kolom) : Theme.lebarSelFolder
            cellHeight: Math.min(Math.round((cellWidth - Theme.j16) * 0.72), Theme.tinggiSampulMaks) + Theme.j40 + Theme.j16
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Gulir {}
            cacheBuffer: 300
            activeFocusOnTab: true
            Accessible.name: qsTr("Daftar folder")
            Keys.onReturnPressed: if (currentItem) currentItem.buka()
            Keys.onSpacePressed: if (currentItem) currentItem.buka()

            delegate: Item {
                id: sel
                required property var modelData
                required property int index
                function buka() {
                    if (modelData.punyaAnak) folder.masuk(modelData.source, modelData.rel)
                    else akar.lihat(folder.saringanUntuk(modelData.source, modelData.rel, modelData.nama))
                }
                width: kisi.cellWidth
                height: kisi.cellHeight

                KartuKoleksi {
                    anchors.fill: parent
                    anchors.margins: Theme.j8
                    url: sel.modelData.url
                    urls: sel.modelData.urls
                    judul: sel.modelData.nama
                    info: akar.angka(sel.modelData.jumlah) + qsTr(" foto")
                          + (sel.modelData.subfolder > 0 ? " · " + qsTr("%1 folder").arg(sel.modelData.subfolder) : "")
                    terfokus: kisi.activeFocus && sel.GridView.isCurrentItem
                    onDiklik: sel.buka()
                }
            }

            // Foto terbaru di bawah kartu: satu gulir dengan folder, dari thumbnail lokal
            footer: Item {
                width: kisi.width
                height: folder.dinding.length > 0 ? Theme.j8 + Theme.j40 + Theme.j8 + folder.tinggiDinding + Theme.j24 : 0
                visible: folder.dinding.length > 0
                onWidthChanged: folder.atur(width - Theme.j16)
                Component.onCompleted: folder.atur(width - Theme.j16)

                RowLayout {
                    x: Theme.j8
                    y: Theme.j8
                    width: parent.width - Theme.j16
                    height: Theme.j40
                    Teks { peran: "besar"; text: folder.judulDinding; Layout.fillWidth: true }
                    Tombol { visible: !folder.dalam; teks: qsTr("Lihat semua"); onDiklik: akar.semuaFoto() }
                }
                Item {
                    x: Theme.j8
                    y: Theme.j8 + Theme.j40 + Theme.j8
                    width: parent.width - Theme.j16
                    height: folder.tinggiDinding

                    Repeater {
                        model: folder.dinding
                        delegate: Item {
                            id: ubin
                            required property var modelData
                            x: modelData.x
                            y: modelData.y
                            width: modelData.w
                            height: modelData.h
                            Rectangle { anchors.fill: parent; color: Theme.sorot }
                            Image {
                                anchors.fill: parent
                                asynchronous: true
                                fillMode: Image.PreserveAspectCrop
                                source: ubin.modelData.url
                            }
                            Rectangle { anchors.fill: parent; color: Theme.layarSorot; visible: tekanUbin.containsMouse }
                            SudutFoto {}
                            MouseArea {
                                id: tekanUbin
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: akar.bukaFoto(folder.saringanDinding(), ubin.modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }

    KeadaanKosong {
        anchors.centerIn: parent
        visible: folder.anak.length === 0 && !folder.dalam
        ikon: "folder"
        judul: pindai.aktif ? qsTr("Menyiapkan foto Anda") : qsTr("Belum ada foto")
        keterangan: pindai.aktif ? qsTr("Folder akan muncul di sini sebentar lagi.")
                                 : qsTr("Pilih folder berisi foto. Foto Anda tetap di tempatnya dan tidak diubah.")
        aksi: pindai.aktif ? "" : qsTr("Pilih folder foto")
        onDiklik: akar.tambahFolder()
    }
}
