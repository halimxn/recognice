import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: akar
    signal tambahFolder()
    signal cariLokasi(int id)
    property int kandidatHapus: -1
    property string labelHapus: ""

    function angka(n) { return n.toLocaleString(Qt.locale("id_ID"), "f", 0) }
    function ringkas(s) {
        let t = angka(s.ok) + qsTr(" foto")
        if (s.gagal) t += qsTr(" · %1 tidak bisa dibuka").arg(s.gagal)
        if (s.hilang) t += qsTr(" · %1 sudah tidak ada").arg(s.hilang)
        return t
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        anchors.bottomMargin: Theme.j16
        spacing: Theme.j4
        visible: pindai.sumber.length > 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiKepala
            Teks {
                anchors.verticalCenter: parent.verticalCenter
                peran: "judul"
                width: parent.width - Theme.j40 * 5
                text: qsTr("Lokasi foto")
            }
            Tombol {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                teks: qsTr("Tambah folder"); ikon: "tambah"; jenis: "utama"
                onDiklik: akar.tambahFolder()
            }
        }
        Teks {
            color: Theme.teks2
            text: qsTr("Folder yang fotonya tampil di Recognice. Foto Anda tidak pernah diubah atau dipindah.")
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.j12
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: pindai.sumber
            boundsBehavior: Flickable.StopAtBounds
            spacing: Theme.j4
            ScrollBar.vertical: Gulir {}

            delegate: Kartu {
                id: baris
                required property var modelData
                readonly property bool sedang: pindai.sumberAktif === modelData.id
                readonly property bool tersambung: galeri.tersambung[String(modelData.id)] ?? true
                width: ListView.view.width
                height: sedang ? Theme.barisSumberAktif : Theme.barisSumber

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: Theme.j16
                    anchors.rightMargin: Theme.j12
                    height: Theme.barisSumber
                    spacing: Theme.j16

                    Ikon { nama: "sumber"; warna: baris.tersambung ? Theme.teks : Theme.teks2; ukuran: Theme.ikonRel }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Teks { text: baris.modelData.label; font.weight: Font.DemiBold; Layout.fillWidth: true }
                        Teks {
                            peran: "kecil"
                            color: Theme.teks2
                            text: (baris.tersambung ? akar.ringkas(baris.modelData) : qsTr("Folder ini tidak ditemukan, tetapi fotonya tetap bisa dilihat. Kalau foldernya dipindah atau diganti nama, tunjukkan lokasi barunya."))
                                + "  ·  " + baris.modelData.jalur
                            Layout.fillWidth: true
                        }
                    }
                    Tombol {
                        visible: !baris.sedang && !baris.tersambung
                        teks: qsTr("Tunjukkan lokasi baru")
                        ikon: "folder"
                        mati: pindai.aktif || pindai.mencariLokasi
                        onDiklik: akar.cariLokasi(baris.modelData.id)
                    }
                    Tombol {
                        visible: !baris.sedang && baris.tersambung
                        teks: qsTr("Periksa foto baru")
                        ikon: "ulang"
                        onDiklik: pindai.pindai(baris.modelData.id)
                    }
                    Tombol {
                        visible: baris.sedang
                        teks: pindai.dijeda && !pindai.karenaBaterai ? qsTr("Lanjutkan") : qsTr("Jeda")
                        ikon: pindai.dijeda && !pindai.karenaBaterai ? "putar" : "jeda"
                        mati: pindai.karenaBaterai
                        onDiklik: pindai.alihkanJeda()
                    }
                    Tombol {
                        visible: baris.sedang
                        teks: qsTr("Hentikan")
                        onDiklik: pindai.hentikan()
                    }
                    Tombol {
                        visible: !baris.sedang
                        mati: pindai.aktif
                        jenis: "ikon"; ikon: "hapus"; petunjuk: qsTr("Berhenti menampilkan folder ini")
                        onDiklik: { akar.kandidatHapus = baris.modelData.id; akar.labelHapus = baris.modelData.label }
                    }
                }

                Column {
                    visible: baris.sedang
                    x: Theme.j16
                    y: Theme.barisSumber - Theme.j8
                    width: parent.width - Theme.j32
                    spacing: Theme.j4
                    Progres { width: parent.width; nilai: pindai.total > 0 ? pindai.kini / pindai.total : 0 }
                    Teks {
                        peran: "kecil"
                        color: Theme.teks2
                        text: pindai.karenaBaterai ? qsTr("Berhenti sebentar karena laptop tidak dicas. Lanjut sendiri saat dicas.")
                            : pindai.dijeda ? qsTr("Dijeda")
                            : pindai.total > 0 ? qsTr("Membaca foto %1 dari %2").arg(akar.angka(pindai.kini)).arg(akar.angka(pindai.total))
                            : qsTr("Mencari foto…")
                    }
                }
            }
        }

        // Kemajuan pengenalan wajah juga terlihat saat tidak berjalan
        Kartu {
            visible: pindai.tahap !== "wajah" && pindai.wajahTotal > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.kartuWajah
            Layout.topMargin: Theme.j8
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j16
                anchors.rightMargin: Theme.j12
                spacing: Theme.j16
                Ikon { nama: "orang"; ukuran: Theme.ikonRel }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.j4
                    Teks { font.weight: Font.DemiBold; text: qsTr("Pengenalan wajah") }
                    Progres { Layout.fillWidth: true; nilai: pindai.wajahSelesai / pindai.wajahTotal }
                    Teks {
                        peran: "kecil"
                        color: Theme.teks2
                        text: pindai.wajahSelesai >= pindai.wajahTotal ? qsTr("Semua %1 foto sudah dikenali wajahnya.").arg(akar.angka(pindai.wajahTotal))
                            : qsTr("%1 dari %2 foto sudah dikenali wajahnya. Sisanya dikerjakan saat aplikasi terbuka.")
                                .arg(akar.angka(pindai.wajahSelesai)).arg(akar.angka(pindai.wajahTotal))
                    }
                }
                Tombol {
                    visible: pindai.wajahSelesai < pindai.wajahTotal
                    teks: qsTr("Lanjutkan sekarang"); ikon: "putar"
                    mati: pindai.aktif || pindai.mencariLokasi
                    onDiklik: pindai.lanjutkanWajah()
                }
            }
        }

        // Pengenalan wajah berjalan untuk semua sumber
        Kartu {
            visible: pindai.tahap === "wajah"
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.kartuWajah
            Layout.topMargin: Theme.j8
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j16
                anchors.rightMargin: Theme.j12
                spacing: Theme.j16
                Ikon { nama: "orang"; ukuran: Theme.ikonRel }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.j4
                    Teks { font.weight: Font.DemiBold; text: qsTr("Mengenali wajah") }
                    Progres { Layout.fillWidth: true; nilai: pindai.total > 0 ? pindai.kini / pindai.total : 0 }
                    Teks {
                        peran: "kecil"
                        color: Theme.teks2
                        text: pindai.karenaBaterai ? qsTr("Berhenti sebentar karena laptop tidak dicas. Lanjut sendiri saat dicas.")
                            : pindai.dijeda ? qsTr("Dijeda")
                            : pindai.total > 0 ? qsTr("%1 dari %2 foto. Aplikasi boleh ditutup, nanti dilanjutkan sendiri.").arg(akar.angka(pindai.kini)).arg(akar.angka(pindai.total))
                            : qsTr("Menyiapkan pengenal wajah. Pertama kali bisa sampai dua menit.")
                    }
                }
                Tombol {
                    teks: pindai.dijeda && !pindai.karenaBaterai ? qsTr("Lanjutkan") : qsTr("Jeda")
                    ikon: pindai.dijeda && !pindai.karenaBaterai ? "putar" : "jeda"
                    mati: pindai.karenaBaterai
                    onDiklik: pindai.alihkanJeda()
                }
                Tombol { teks: qsTr("Hentikan"); onDiklik: pindai.hentikan() }
            }
        }

        Teks {
            visible: pindai.pesan !== ""
            color: Theme.teks2
            text: pindai.pesan
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            Layout.fillWidth: true
            Layout.topMargin: Theme.j12
        }
    }

    KeadaanKosong {
        anchors.centerIn: parent
        visible: pindai.sumber.length === 0
        ikon: "sumber"
        judul: qsTr("Belum ada folder foto")
        keterangan: qsTr("Tambahkan folder berisi foto. Foto Anda tetap di tempatnya dan tidak diubah.")
        aksi: qsTr("Tambah folder")
        onDiklik: akar.tambahFolder()
    }

    // Konfirmasi: tindakan ini menghapus data galeri, bukan foto
    Rectangle {
        anchors.fill: parent
        visible: akar.kandidatHapus >= 0
        color: Theme.tirai
        MouseArea { anchors.fill: parent }

        Kartu {
            anchors.centerIn: parent
            width: Theme.lebarDialog
            height: isiDialog.implicitHeight + bilah.height + Theme.j24 * 2

            ColumnLayout {
                id: isiDialog
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.j24
                spacing: Theme.j12
                Teks { peran: "besar"; text: qsTr("Berhenti menampilkan “%1”?").arg(akar.labelHapus); Layout.fillWidth: true }
                Teks {
                    color: Theme.teks2
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    text: qsTr("Foto di folder itu tidak dihapus dan tidak diubah. Yang dihapus hanya data Recognice untuk folder ini, termasuk nama orang di foto-fotonya.")
                    Layout.fillWidth: true
                }
            }
            Rectangle {
                id: bilah
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 1
                height: Theme.j40 + Theme.j24
                radius: Theme.sudut
                color: Theme.kanvas
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.j16
                    spacing: Theme.j8
                    Tombol { Layout.fillWidth: true; teks: qsTr("Batal"); onDiklik: akar.kandidatHapus = -1 }
                    Tombol {
                        Layout.fillWidth: true
                        teks: qsTr("Berhenti menampilkan"); jenis: "utama"
                        onDiklik: { pindai.hapus(akar.kandidatHapus); akar.kandidatHapus = -1 }
                    }
                }
            }
        }
    }
}
