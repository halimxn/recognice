import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    FolderDialog { id: dialogCadang; title: qsTr("Simpan cadangan ke folder"); onAccepted: alat.cadangkan(selectedFolder.toString()) }
    FolderDialog { id: dialogPulih; title: qsTr("Pilih folder cadangan"); onAccepted: alat.pilihPulih(selectedFolder.toString()) }

    // Satu baris pengaturan: ikon, judul, keterangan, kontrol di kanan
    component KartuAtur: Kartu {
        id: kartu
        property string ikon: ""
        property string judul: ""
        property string keterangan: ""
        default property alias kontrol: tempat.data
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.j40 + Theme.j32
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.j16
            anchors.rightMargin: Theme.j16
            spacing: Theme.j16
            Ikon { nama: kartu.ikon; ukuran: Theme.ikonRel }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Teks { text: kartu.judul; Layout.fillWidth: true }
                Teks { peran: "kecil"; color: Theme.teks2; text: kartu.keterangan; Layout.fillWidth: true }
            }
            Row { id: tempat; spacing: Theme.j8 }
        }
    }

    component Sakelar: Item {
        id: sakelar
        property bool nyala: false
        property string nama: ""
        signal dialihkan()
        width: label.implicitWidth + Theme.j12 + Theme.lebarSakelar
        height: Theme.tinggiSakelar
        activeFocusOnTab: true
        Accessible.role: Accessible.CheckBox
        Accessible.name: nama
        Accessible.checked: nyala
        Keys.onSpacePressed: dialihkan()
        Teks { id: label; anchors.verticalCenter: parent.verticalCenter; text: sakelar.nyala ? qsTr("Nyala") : qsTr("Mati") }
        Rectangle {
            anchors.right: parent.right
            width: Theme.lebarSakelar
            height: Theme.tinggiSakelar
            radius: height / 2
            color: sakelar.nyala ? Theme.aksen : "transparent"
            border.width: sakelar.nyala && !sakelar.activeFocus ? 0 : 1
            border.color: sakelar.activeFocus ? Theme.fokus : Theme.teks2
            Rectangle {
                x: sakelar.nyala ? parent.width - width - Theme.j4 : Theme.j4
                anchors.verticalCenter: parent.verticalCenter
                width: Theme.bulatSakelar
                height: Theme.bulatSakelar
                radius: width / 2
                color: sakelar.nyala ? Theme.padaAksen : Theme.teks2
                Behavior on x { NumberAnimation { duration: Theme.gerakCepat; easing.type: Easing.OutCubic } }
            }
        }
        MouseArea { anchors.fill: parent; onClicked: sakelar.dialihkan() }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: isi.implicitHeight + Theme.j32
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        ScrollBar.vertical: Gulir {}

        ColumnLayout {
            id: isi
            x: Theme.tepiIsi
            width: parent.width - Theme.tepiIsi - Theme.j24
            spacing: Theme.j4

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.tinggiKepala
                Teks {
                    anchors.verticalCenter: parent.verticalCenter
                    peran: "judul"
                    text: qsTr("Pengaturan")
                }
            }

            Teks { font.weight: Font.DemiBold; text: qsTr("Tampilan"); Layout.bottomMargin: Theme.j4 }
            KartuAtur {
                ikon: "atur"
                judul: qsTr("Tema")
                keterangan: qsTr("Warna aplikasi. Foto selalu dibuka di latar gelap.")
                Repeater {
                    model: [{ k: "auto", t: qsTr("Ikuti Windows") }, { k: "gelap", t: qsTr("Gelap") }, { k: "terang", t: qsTr("Terang") }]
                    delegate: Pil {
                        required property var modelData
                        teks: modelData.t
                        aktif: pengaturan.tema === modelData.k
                        onDipilih: pengaturan.aturTema(modelData.k)
                    }
                }
            }

            KartuAtur {
                ikon: "galeri"
                judul: qsTr("Halaman pertama")
                keterangan: qsTr("Pilih Folder kalau aplikasi terasa lambat saat dibuka.")
                Repeater {
                    model: [{ k: "galeri", t: qsTr("Galeri") }, { k: "folder", t: qsTr("Folder") }]
                    delegate: Pil {
                        required property var modelData
                        teks: modelData.t
                        aktif: pengaturan.halamanAwal === modelData.k
                        onDipilih: pengaturan.aturHalamanAwal(modelData.k)
                    }
                }
            }

            Teks { font.weight: Font.DemiBold; text: qsTr("Baterai"); Layout.topMargin: Theme.j24; Layout.bottomMargin: Theme.j4 }
            KartuAtur {
                ikon: "jeda"
                judul: qsTr("Berhenti saat laptop tidak dicas")
                keterangan: qsTr("Membaca foto dan mengenali wajah berhenti sebentar sampai laptop dicas, supaya baterai awet.")
                Sakelar {
                    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    nama: qsTr("Berhenti saat laptop tidak dicas")
                    nyala: pengaturan.jedaBaterai
                    onDialihkan: pengaturan.aturJedaBaterai(!pengaturan.jedaBaterai)
                }
            }

            Teks { font.weight: Font.DemiBold; text: qsTr("Data"); Layout.topMargin: Theme.j24; Layout.bottomMargin: Theme.j4 }
            KartuAtur {
                ikon: "folder"
                judul: qsTr("Tempat data Recognice")
                keterangan: alat.lokasiData
            }
            KartuAtur {
                ikon: "orang"
                judul: qsTr("Pengenal wajah")
                keterangan: qsTr("Berjalan di laptop ini tanpa internet. Foto dan wajah tidak dikirim ke mana pun.")
            }
            KartuAtur {
                ikon: "salin"
                judul: qsTr("Cadangan")
                keterangan: qsTr("Menyimpan nama orang dan koreksi Anda. Foto tidak ikut disalin.")
                Tombol { teks: qsTr("Buat cadangan"); mati: alat.sibuk; onDiklik: dialogCadang.open() }
                Tombol { teks: qsTr("Pulihkan"); mati: alat.sibuk; onDiklik: dialogPulih.open() }
            }
            Kartu {
                visible: alat.calonPulih !== ""
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.j40 + Theme.j32
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.j16
                    anchors.rightMargin: Theme.j16
                    spacing: Theme.j8
                    Teks {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        elide: Text.ElideNone
                        text: qsTr("Ganti nama orang dan koreksi Anda dengan isi cadangan ini? Data yang sekarang tetap disimpan sebagai salinan.")
                    }
                    Tombol { teks: qsTr("Batal"); onDiklik: alat.batalPulih() }
                    Tombol { teks: qsTr("Pulihkan"); jenis: "utama"; onDiklik: alat.pulihkan() }
                }
            }
            Teks {
                visible: alat.pesan !== ""
                Layout.fillWidth: true
                Layout.topMargin: Theme.j12
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                color: Theme.teks2
                text: alat.pesan
            }
        }
    }
}
