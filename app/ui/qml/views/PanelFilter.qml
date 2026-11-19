import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Kartu {
    id: akar
    signal tutup()

    property int halaman: 0
    readonly property int perHalaman: 10
    readonly property int jumlahHalaman: Math.max(1, Math.ceil(orang.daftar.length / perHalaman))
    readonly property var pilihanOrang: galeri.panel.orang_panel || []
    property var tahun: []
    onVisibleChanged: if (visible) tahun = galeri.tahunTersedia()

    function ubah(kunci, nilai) {
        const p = Object.assign({}, galeri.panel)
        p[kunci] = nilai
        galeri.aturPanel(p)
    }
    function alih(kunci, nilai) { ubah(kunci, galeri.panel[kunci] === nilai ? 0 : nilai) }
    function alihOrang(id) {
        const a = pilihanOrang.slice(), i = a.indexOf(id)
        if (i >= 0) a.splice(i, 1); else a.push(id)
        ubah("orang_panel", a)
    }

    component Judul: Teks {
        peran: "kecil"
        color: Theme.teks2
        Layout.topMargin: Theme.j16
        Layout.bottomMargin: Theme.j8
        Layout.fillWidth: true
    }

    RowLayout {
        id: kepala
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: Theme.j16
        anchors.rightMargin: Theme.j8
        height: Theme.j40 + Theme.j8
        Teks { font.weight: Font.DemiBold; font.pixelSize: Theme.ukTeks + 1; text: qsTr("Filter"); Layout.fillWidth: true }
        Tombol { jenis: "ikon"; ikon: "tutup"; petunjuk: qsTr("Tutup filter"); onDiklik: akar.tutup() }
    }

    Flickable {
        anchors.top: kepala.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.j8
        contentHeight: isi.implicitHeight + Theme.j8
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        ScrollBar.vertical: Gulir {}

        ColumnLayout {
            id: isi
            x: Theme.j16
            width: parent.width - Theme.j32
            spacing: 0

            Teks { visible: akar.tahun.length > 1; peran: "kecil"; color: Theme.teks2; text: qsTr("Tahun"); Layout.bottomMargin: Theme.j8 }
            Flow {
                visible: akar.tahun.length > 1
                Layout.fillWidth: true
                Layout.bottomMargin: Theme.j16
                spacing: Theme.j8
                Repeater {
                    model: akar.tahun
                    delegate: Pil {
                        required property int modelData
                        teks: String(modelData)
                        aktif: galeri.panel.tahun === modelData
                        onDipilih: akar.alih("tahun", modelData)
                    }
                }
            }

            RowLayout {
                visible: orang.daftar.length > 0
                Layout.fillWidth: true
                Layout.bottomMargin: Theme.j4
                Teks { peran: "kecil"; color: Theme.teks2; text: qsTr("Orang"); Layout.fillWidth: true }
                Tombol { visible: akar.jumlahHalaman > 1; jenis: "ikon"; ikon: "kiri"; petunjuk: qsTr("Sebelumnya"); mati: akar.halaman === 0; onDiklik: akar.halaman-- }
                Tombol { visible: akar.jumlahHalaman > 1; jenis: "ikon"; ikon: "kanan"; petunjuk: qsTr("Berikutnya"); mati: akar.halaman >= akar.jumlahHalaman - 1; onDiklik: akar.halaman++ }
            }

            GridLayout {
                visible: orang.daftar.length > 0
                Layout.fillWidth: true
                columns: 5
                columnSpacing: 0
                rowSpacing: 0
                Repeater {
                    model: orang.daftar.slice(akar.halaman * akar.perHalaman, (akar.halaman + 1) * akar.perHalaman)
                    delegate: Item {
                        id: wj
                        required property var modelData
                        readonly property bool dipilih: akar.pilihanOrang.indexOf(modelData.id) >= 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: Theme.avatarFilter + Theme.j32 + Theme.j4
                        activeFocusOnTab: true
                        Accessible.role: Accessible.CheckBox
                        Accessible.name: modelData.nama || qsTr("Siapa ini?")
                        Accessible.checked: dipilih
                        Keys.onSpacePressed: akar.alihOrang(modelData.id)

                        Image {
                            id: muka
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: Theme.j2
                            width: Theme.avatarFilter
                            height: Theme.avatarFilter
                            sourceSize: Qt.size(96, 96)
                            asynchronous: true
                            source: wj.modelData.url
                        }
                        Rectangle {
                            anchors.centerIn: muka
                            width: muka.width + Theme.j4
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.width: wj.dipilih || wj.activeFocus ? Theme.j2 : tekan.containsMouse ? 1 : 0
                            border.color: wj.activeFocus ? Theme.fokus : wj.dipilih ? Theme.aksen : Theme.teks2
                        }
                        Teks {
                            anchors.top: muka.bottom
                            anchors.topMargin: Theme.j4
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            peran: "kecil"
                            font.weight: wj.dipilih ? Font.DemiBold : Font.Normal
                            color: wj.dipilih ? Theme.teks : Theme.teks2
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            text: wj.modelData.nama || qsTr("Siapa ini?")
                        }
                        MouseArea { id: tekan; anchors.fill: parent; hoverEnabled: true; onClicked: akar.alihOrang(wj.modelData.id) }
                    }
                }
            }

            RowLayout {
                visible: orang.daftar.length > 0
                Layout.fillWidth: true
                Layout.topMargin: Theme.j8
                spacing: Theme.j8
                Rectangle {
                    id: centang
                    readonly property bool nyala: !!galeri.panel.salah_satu
                    Layout.preferredWidth: Theme.kotakCentang
                    Layout.preferredHeight: Theme.kotakCentang
                    radius: Theme.sudutKontrol
                    color: nyala ? Theme.aksenIsi : "transparent"
                    border.width: nyala ? 0 : 1
                    border.color: activeFocus ? Theme.fokus : Theme.teks2
                    activeFocusOnTab: true
                    Accessible.role: Accessible.CheckBox
                    Accessible.name: labelCentang.text
                    Accessible.checked: nyala
                    Keys.onSpacePressed: akar.ubah("salah_satu", !nyala)
                    Ikon { anchors.centerIn: parent; ukuran: Theme.j12; nama: centang.nyala ? "centang" : ""; warna: Theme.padaAksen }
                    MouseArea { anchors.fill: parent; onClicked: akar.ubah("salah_satu", !parent.nyala) }
                }
                Teks {
                    id: labelCentang
                    Layout.fillWidth: true
                    peran: "kecil"
                    color: Theme.teks2
                    wrapMode: Text.WordWrap
                    text: qsTr("Cukup salah satu orang terpilih ada di foto")
                }
            }

            Judul { text: qsTr("Sumber") }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.j8
                Repeater {
                    model: pindai.sumber
                    delegate: Rectangle {
                        id: kartuSumber
                        required property var modelData
                        readonly property bool dipilih: galeri.panel.source === modelData.id
                        width: Theme.folderSumber + Theme.j24
                        height: Theme.folderSumber + Theme.j8
                        radius: Theme.sudutKontrol + Theme.j4
                        color: dipilih ? Theme.sorotKuat : areaSumber.containsMouse ? Theme.sorot : "transparent"
                        border.width: dipilih ? 1 : 0
                        border.color: Theme.aksen
                        Accessible.role: Accessible.RadioButton
                        Accessible.name: modelData.label
                        IkonFolder {
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: Theme.j4
                            width: Theme.folderSumber - Theme.j16
                            height: width * 0.83
                        }
                        Teks {
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: Theme.j4
                            width: parent.width - Theme.j8
                            x: Theme.j4
                            horizontalAlignment: Text.AlignHCenter
                            peran: "kecil"
                            color: Theme.teks2
                            text: kartuSumber.modelData.label
                        }
                        MouseArea { id: areaSumber; anchors.fill: parent; hoverEnabled: true; onClicked: akar.alih("source", kartuSumber.modelData.id) }
                    }
                }
            }

            Judul { text: qsTr("Orientasi") }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.j8
                Repeater {
                    model: [{ k: "potret", t: qsTr("Potret") }, { k: "lanskap", t: qsTr("Lanskap") }, { k: "persegi", t: qsTr("Persegi") }]
                    delegate: Pil {
                        required property var modelData
                        teks: modelData.t
                        aktif: galeri.panel.orientasi === modelData.k
                        onDipilih: akar.alih("orientasi", modelData.k)
                    }
                }
            }

            Judul { text: qsTr("Resolusi") }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.j8
                Repeater {
                    model: [{ k: 1280, t: "HD+" }, { k: 1920, t: "FHD+" }, { k: 3840, t: "4K+" }]
                    delegate: Pil {
                        required property var modelData
                        teks: modelData.t
                        aktif: galeri.panel.resolusi === modelData.k
                        onDipilih: akar.alih("resolusi", modelData.k)
                    }
                }
            }
        }
    }
}
