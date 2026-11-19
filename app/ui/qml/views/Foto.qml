import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: akar
    objectName: "galeriHalaman"
    property bool filterTerbuka: false
    property string tanggalKini: ""
    signal bukaFoto(int indeks, rect kotak)
    signal bukaKoleksi(var saringan)
    signal tambahFolder()
    signal kembali()
    signal kelolaWajah(int id)

    readonly property var ukuranBaris: [120, 170, 260]
    readonly property bool sempit: width < Theme.batasSempit

    FolderDialog {
        id: dialogEkspor
        title: qsTr("Salin foto ke folder")
        onAccepted: alat.ekspor(selectedFolder.toString())
    }

    Timer {
        id: tundaTanggal
        interval: 80
        onTriggered: akar.tanggalKini = galeri.tanggalDi(daftar.contentY)
    }
    Connections { target: galeri; function onTataBerubah() { tundaTanggal.restart() } }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: Theme.tepiIsi
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.tinggiKepala
                spacing: Theme.j12

                Tombol {
                    visible: galeri.adaSaring
                    jenis: "ikon"; ikon: "kembali"; petunjuk: qsTr("Kembali")
                    onDiklik: akar.kembali()
                }
                Teks {
                    peran: "judul"
                    text: galeri.adaSaring ? galeri.labelSaring : qsTr("Galeri")
                    Layout.maximumWidth: Theme.lebarJudulMaks
                }
                Rectangle {
                    visible: galeri.jumlah > 0 && akar.tanggalKini !== "" && !akar.sempit
                    Layout.preferredHeight: Theme.tinggiKontrol
                    Layout.preferredWidth: labelTanggal.implicitWidth + Theme.j32
                    radius: height / 2
                    color: Theme.isi
                    Teks { id: labelTanggal; anchors.centerIn: parent; peran: "sedang"; color: Theme.padaIsi; text: akar.tanggalKini }
                }
                Item { Layout.fillWidth: true }

                Teks {
                    visible: alat.sibuk || alat.pesan !== ""
                    color: Theme.teks2
                    Layout.maximumWidth: Theme.ruangSampingStrip
                    text: alat.sibuk ? qsTr("Menyalin %1 / %2").arg(alat.kini).arg(alat.total) : alat.pesan
                }
                Tombol {
                    visible: galeri.adaSaring && galeri.jumlah > 0
                    jenis: "ikon"; latar: true; ikon: "salin"; petunjuk: qsTr("Salin foto-foto ini ke folder lain")
                    mati: alat.sibuk
                    onDiklik: dialogEkspor.open()
                }
                Tombol {
                    visible: galeri.orangAktif >= 0
                    jenis: "ikon"; latar: true; ikon: "wajah"; petunjuk: qsTr("Periksa wajah orang ini")
                    onDiklik: akar.kelolaWajah(galeri.orangAktif)
                }

                // Saat aktif: garis aksen, lencana jumlah, dan tanda hapus
                Rectangle {
                    id: pilFilter
                    readonly property bool aktif: akar.filterTerbuka || galeri.jumlahPanel > 0
                    visible: galeri.jumlah > 0 || galeri.adaSaring || galeri.jumlahPanel > 0
                    Layout.preferredHeight: Theme.tinggiKontrol
                    Layout.preferredWidth: isiFilter.implicitWidth + Theme.j24
                    radius: height / 2
                    color: tekanFilter.containsMouse ? Theme.isiSorot : Theme.isi
                    border.width: aktif ? 1 : 0
                    border.color: Theme.aksen
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: qsTr("Filter")
                    Keys.onSpacePressed: akar.filterTerbuka = !akar.filterTerbuka
                    Keys.onReturnPressed: akar.filterTerbuka = !akar.filterTerbuka

                    MouseArea { id: tekanFilter; anchors.fill: parent; hoverEnabled: true; onClicked: akar.filterTerbuka = !akar.filterTerbuka }
                    Row {
                        id: isiFilter
                        anchors.centerIn: parent
                        spacing: Theme.j8
                        Rectangle {
                            visible: galeri.jumlahPanel > 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: Theme.j16 + Theme.j4
                            height: width
                            radius: width / 2
                            color: Theme.aksenIsi
                            Teks { anchors.centerIn: parent; peran: "kecil"; color: Theme.padaAksen; text: galeri.jumlahPanel }
                        }
                        Ikon { visible: galeri.jumlahPanel === 0; nama: "filter"; anchors.verticalCenter: parent.verticalCenter; warna: Theme.padaIsi }
                        Teks { text: qsTr("Filter"); color: Theme.padaIsi; anchors.verticalCenter: parent.verticalCenter }
                        Tombol {
                            visible: galeri.jumlahPanel > 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: Theme.j24; height: Theme.j24
                            jenis: "ikon"; ikon: "tutup"; petunjuk: qsTr("Hapus semua filter")
                            warnaIsi: Theme.padaIsi; warnaSorot: Theme.isiSorot
                            onDiklik: galeri.aturPanel({})
                        }
                    }
                }

                Tombol {
                    id: tombolUkuran
                    jenis: "ikon"; latar: true; ikon: "ukuran"; petunjuk: qsTr("Ukuran foto")
                    visible: galeri.jumlah > 0
                    onDiklik: menuUkuran.open()

                    Popup {
                        id: menuUkuran
                        y: parent.height + Theme.j4
                        x: parent.width - width
                        width: 168
                        padding: Theme.j4
                        background: Kartu {}
                        contentItem: Column {
                            Repeater {
                                model: [{ i: "kecil", t: qsTr("Foto kecil") }, { i: "sedang", t: qsTr("Foto sedang") }, { i: "besar", t: qsTr("Foto besar") }]
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    readonly property bool kini: pengaturan.tinggiBaris === akar.ukuranBaris[index]
                                    width: parent.width
                                    height: Theme.tinggiSaringUkuran
                                    radius: Theme.sudutKontrol
                                    color: kini ? Theme.sorotKuat : areaUkuran.containsMouse ? Theme.sorot : "transparent"
                                    Row {
                                        anchors.verticalCenter: parent.verticalCenter
                                        x: Theme.j12
                                        spacing: Theme.j12
                                        Ikon { nama: parent.parent.modelData.i; anchors.verticalCenter: parent.verticalCenter }
                                        Teks { text: parent.parent.modelData.t; anchors.verticalCenter: parent.verticalCenter }
                                    }
                                    MouseArea {
                                        id: areaUkuran
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: { akar.aturUkuran(akar.ukuranBaris[parent.index]); menuUkuran.close() }
                                    }
                                }
                            }
                        }
                    }
                }

                Tombol {
                    visible: !galeri.adaSaring && !akar.sempit
                    teks: qsTr("Tambah folder"); ikon: "tambah"; jenis: "utama"
                    onDiklik: akar.tambahFolder()
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Flickable {
                    id: daftar
                    objectName: "daftar"
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: galeri.tinggiTotal
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    maximumFlickVelocity: 7000
                    flickDeceleration: 2600
                    onContentYChanged: { galeri.lihat(contentY, height); tundaTanggal.restart() }
                    onHeightChanged: galeri.lihat(contentY, height)
                    onWidthChanged: if (width > 0) susunTunda.restart()
                    visible: galeri.jumlah > 0
                    activeFocusOnTab: true
                    Accessible.name: qsTr("Daftar foto")

                    property int fokus: -1
                    function pindahFokus(i) {
                        fokus = Math.max(0, Math.min(galeri.jumlah - 1, i))
                        const y = galeri.yFoto(fokus), h = pengaturan.tinggiBaris
                        if (y < contentY) contentY = y
                        else if (y + h > contentY + height) contentY = Math.min(y + h - height + galeri.jarak, Math.max(0, contentHeight - height))
                    }
                    function arah(fungsi) { pindahFokus(fokus < 0 ? galeri.fotoDi(contentY) : fungsi(fokus)) }
                    Keys.onLeftPressed: arah((i) => i - 1)
                    Keys.onRightPressed: arah((i) => i + 1)
                    Keys.onUpPressed: arah((i) => galeri.tetangga(i, -1))
                    Keys.onDownPressed: arah((i) => galeri.tetangga(i, 1))
                    Keys.onReturnPressed: if (fokus >= 0) akar.bukaFoto(fokus, Qt.rect(0, 0, 0, 0))
                    Keys.onEnterPressed: if (fokus >= 0) akar.bukaFoto(fokus, Qt.rect(0, 0, 0, 0))

                    Timer {
                        id: susunTunda
                        interval: 60
                        onTriggered: { galeri.atur(daftar.width); galeri.lihat(daftar.contentY, daftar.height) }
                    }

                    // Deret pembuka, ikut tergulir bersama foto
                    Row {
                        visible: galeri.koleksi.length > 0
                        width: daftar.width
                        height: galeri.tinggiKoleksi - Theme.j16
                        spacing: Theme.j12
                        Repeater {
                            model: galeri.koleksi
                            delegate: KartuKoleksi {
                                required property var modelData
                                width: (daftar.width - Theme.j12 * (galeri.koleksi.length - 1)) / galeri.koleksi.length
                                height: parent.height
                                url: modelData.url
                                judul: modelData.judul
                                info: modelData.info
                                onDiklik: akar.bukaKoleksi(modelData.saring)
                            }
                        }
                    }

                    Repeater {
                        model: galeri
                        delegate: Item {
                            id: slotBaris
                            required property int posY
                            required property int tinggiSlot
                            required property string jenis
                            required property var isi
                            y: posY
                            width: daftar.width
                            height: tinggiSlot
                            visible: jenis === "foto"
                            // Sel dipakai ulang: baris berganti isi hanya mengubah ikatan, sel tidak dibuat ulang.
                            // Membuat ulang sel adalah yang membuat seret penggulir tersendat (dev/bench/HASIL.md).
                            property int kapasitas: 0
                            function tampung() { if (jenis === "foto") kapasitas = Math.max(kapasitas, isi.length) }
                            onIsiChanged: tampung()
                            Component.onCompleted: tampung()

                            Repeater {
                                model: slotBaris.kapasitas
                                delegate: Item {
                                    id: sel
                                    required property int index
                                    readonly property var modelData: slotBaris.jenis === "foto" && index < slotBaris.isi.length ? slotBaris.isi[index] : null
                                    visible: modelData !== null
                                    x: modelData ? modelData.x : 0
                                    width: modelData ? modelData.w : 0
                                    height: slotBaris.height - galeri.jarak

                                    Rectangle { anchors.fill: parent; color: Theme.sorot }
                                    Image {
                                        id: gambar
                                        anchors.fill: parent
                                        asynchronous: true
                                        cache: true
                                        fillMode: Image.PreserveAspectCrop
                                        source: sel.modelData ? sel.modelData.url : ""
                                        opacity: status === Image.Ready ? 1 : 0
                                        Behavior on opacity { NumberAnimation { duration: Theme.gerakSedang; easing.type: Easing.OutCubic } }
                                    }
                                    Rectangle {
                                        anchors.fill: parent
                                        color: Theme.layarSorot
                                        visible: tekan.containsMouse
                                    }
                                    SudutFoto {}
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: Theme.sudutFoto
                                        color: "transparent"
                                        border.width: Theme.j2
                                        border.color: Theme.fokus
                                        visible: daftar.activeFocus && sel.modelData !== null && daftar.fokus === sel.modelData.indeks
                                    }
                                    MouseArea {
                                        id: tekan
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            const p = sel.mapToItem(null, 0, 0)
                                            akar.bukaFoto(sel.modelData.indeks, Qt.rect(p.x, p.y, sel.width, sel.height))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                KeadaanKosong {
                    anchors.centerIn: parent
                    visible: galeri.jumlah === 0
                    ikon: galeri.adaSaring || galeri.jumlahPanel > 0 ? "filter" : "gambar"
                    judul: galeri.adaSaring || galeri.jumlahPanel > 0 ? qsTr("Tidak ada foto yang cocok")
                         : pindai.aktif ? qsTr("Menyiapkan foto Anda") : qsTr("Belum ada foto")
                    keterangan: galeri.jumlahPanel > 0 ? qsTr("Kurangi pilihan filter untuk melihat lebih banyak foto.")
                        : galeri.adaSaring ? ""
                        : pindai.aktif ? qsTr("Foto akan muncul di sini sebentar lagi.")
                        : qsTr("Pilih folder berisi foto. Foto Anda tetap di tempatnya dan tidak diubah.")
                    aksi: galeri.adaSaring || galeri.jumlahPanel > 0 || pindai.aktif ? "" : qsTr("Pilih folder foto")
                    onDiklik: akar.tambahFolder()
                }
            }
        }

        // Lebar berubah sekali saja: mengatur ulang tata per bingkai berat di HD 520
        Item {
            Layout.fillHeight: true
            Layout.leftMargin: Theme.j12
            Layout.preferredWidth: akar.filterTerbuka ? Theme.lebarFilter : 0
            visible: akar.filterTerbuka
            clip: true

            PanelFilter {
                id: panel
                objectName: "panelFilter"
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: Theme.j8
                anchors.bottomMargin: Theme.j12
                width: Theme.lebarFilter
                x: akar.filterTerbuka ? 0 : Theme.lebarFilter
                Behavior on x { NumberAnimation { duration: Theme.gerakSedang; easing.type: Easing.OutCubic } }
                onTutup: akar.filterTerbuka = false
            }
        }

        // Linimasa selalu di tepi kanan, di luar panel Filter
        Item {
            id: scrubber
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.lebarScrubber
            visible: galeri.jumlah > 0 && galeri.tinggiTotal > daftar.height

            readonly property int atas: Theme.j40 + Theme.j16
            readonly property int bawah: Theme.j40 + Theme.j4
            readonly property real tinggiJalur: height - atas - bawah
            readonly property real frac: daftar.contentHeight > daftar.height
                ? daftar.contentY / (daftar.contentHeight - daftar.height) : 0
            property var penanda: []
            property var titik: []
            function segarkan() { penanda = galeri.penanda(tinggiJalur); titik = galeri.titik(tinggiJalur) }
            function dekatTahun(f) { return penanda.some((p) => Math.abs(p.frac - f) * tinggiJalur < Theme.j12) }
            onTinggiJalurChanged: segarkan()
            Connections { target: galeri; function onTataBerubah() { scrubber.segarkan() } }

            Repeater {
                model: scrubber.titik
                delegate: Rectangle {
                    required property real modelData
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: scrubber.atas + modelData * scrubber.tinggiJalur
                    width: Theme.j4
                    height: 1
                    color: Theme.teks2
                    opacity: 0.6
                    visible: !scrubber.dekatTahun(modelData)
                }
            }
            Repeater {
                model: scrubber.penanda
                delegate: Teks {
                    required property var modelData
                    peran: "kecil"
                    color: Theme.teks3
                    text: modelData.label
                    y: scrubber.atas + modelData.frac * scrubber.tinggiJalur - height / 2
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Theme.j16
                height: Theme.tebalPenanda
                radius: Theme.j2
                color: Theme.aksen
                y: scrubber.atas + Theme.j12 + scrubber.frac * (scrubber.tinggiJalur - Theme.j12)
            }

            MouseArea {
                id: geser
                anchors.fill: parent
                anchors.topMargin: scrubber.atas - Theme.j8
                anchors.bottomMargin: scrubber.bawah
                hoverEnabled: true
                preventStealing: true
                function lompat(py) {
                    const f = Math.min(1, Math.max(0, (py - scrubber.atas) / scrubber.tinggiJalur))
                    daftar.contentY = f * Math.max(0, daftar.contentHeight - daftar.height)
                }
                onPressed: (m) => lompat(m.y + anchors.topMargin)
                onPositionChanged: (m) => { if (pressed) lompat(m.y + anchors.topMargin) }
            }

            Tombol {
                anchors.horizontalCenter: parent.horizontalCenter
                y: Theme.j8
                jenis: "ikon"; ikon: "atas"; petunjuk: qsTr("Gulir ke atas")
                onDiklik: daftar.contentY = Math.max(daftar.contentY - daftar.height * 0.9, 0)
            }
            Tombol {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.j8
                jenis: "ikon"; ikon: "bawah"; petunjuk: qsTr("Gulir ke bawah")
                onDiklik: daftar.contentY = Math.min(daftar.contentY + daftar.height * 0.9, Math.max(0, daftar.contentHeight - daftar.height))
            }

            Kartu {
                visible: geser.containsMouse || geser.pressed
                y: geser.mouseY + geser.anchors.topMargin
                anchors.right: parent.left
                width: labelBulan.implicitWidth + Theme.j24
                height: Theme.tinggiKontrol
                radius: Theme.sudutKontrol
                Teks {
                    id: labelBulan
                    anchors.centerIn: parent
                    text: galeri.bulanDi(Math.max(0, Math.min(1, (geser.mouseY + geser.anchors.topMargin - scrubber.atas) / scrubber.tinggiJalur)))
                }
            }
        }
    }

    function kembalikanFokus() { if (daftar.fokus >= 0) daftar.forceActiveFocus() }

    function aturUkuran(baru) {
        pengaturan.aturTinggiBaris(baru)
        galeri.aturTinggiBaris(baru)
    }

    Connections {
        target: galeri
        function onGeserKe(y) { daftar.contentY = Math.min(y, Math.max(0, daftar.contentHeight - daftar.height)) }
    }
}
