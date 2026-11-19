import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

FocusScope {
    id: akar
    objectName: "lightbox"
    property int indeks: -1
    property var foto: ({})
    property bool infoTerbuka: true
    property string tab: "info"  // info | orang
    property bool kotakWajah: false
    signal bukaOrang(int id)
    signal bukaMirip(int faceId)
    readonly property bool terbuka: indeks >= 0
    readonly property bool panelTampil: infoTerbuka && width >= Theme.minLebarInfo

    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property real zoomMaks: 6

    // Dibaca Main.kontrolDi: bagian bilah judul yang bukan untuk menggeser jendela
    readonly property var kontrolJudul: [tKembali, tWajah, tBuka, tInfo, capMin, capTutup]
    readonly property Item tombolMaks: capMaks

    // Gerak masuk: foto memekar dari ubinnya. 1 = selesai.
    property real masuk: 1
    property rect kotakAsal: Qt.rect(0, 0, 0, 0)
    property int indeksAsal: -1
    NumberAnimation on masuk { id: animMasuk; running: false; from: 0; to: 1; duration: Theme.gerakMasuk; easing.type: Easing.OutCubic }
    NumberAnimation on masuk { id: animKeluar; running: false; to: 0; duration: Theme.gerakSedang; easing.type: Easing.OutCubic; onFinished: akar.tutup() }

    visible: terbuka
    focus: terbuka

    function buka(i, kotak) {
        indeks = i
        muat()
        forceActiveFocus()
        if (kotak && kotak.width > 0) { kotakAsal = kotak; indeksAsal = i; animMasuk.restart() } else { indeksAsal = -1; masuk = 1 }
    }
    function tutup() { animMasuk.stop(); animKeluar.stop(); masuk = 1; indeks = -1; foto = ({}) }
    // Kembali ke ubin asal hanya bila foto yang sama masih terbuka dan tidak diperbesar
    function keluar() { if (indeks === indeksAsal && zoom <= 1) { animMasuk.stop(); animKeluar.start() } else tutup() }
    function muat() {
        foto = galeri.foto(indeks)
        reset()
        strip.positionViewAtIndex(indeks, ListView.Center)
    }
    function reset() { zoom = 1; panX = 0; panY = 0 }
    function geser(d) {
        const i = indeks + d
        if (i >= 0 && i < galeri.jumlah) { indeks = i; muat() }
    }
    function batasi() {
        const mx = Math.max(0, (gambar.lebarTampil * zoom - panggung.width) / 2)
        const my = Math.max(0, (gambar.tinggiTampil * zoom - panggung.height) / 2)
        panX = Math.min(mx, Math.max(-mx, panX))
        panY = Math.min(my, Math.max(-my, panY))
    }
    function zoomKe(nilai, px, py) {
        const baru = Math.min(zoomMaks, Math.max(1, nilai))
        const dx = px - panggung.width / 2 - panX
        const dy = py - panggung.height / 2 - panY
        panX += dx * (1 - baru / zoom)
        panY += dy * (1 - baru / zoom)
        zoom = baru
        batasi()
    }
    function zoomTengah(nilai) { zoomKe(nilai, panggung.width / 2, panggung.height / 2) }

    // Pindai yang berjalan mengubah urutan: indeks dicari ulang dari id foto
    Connections {
        target: galeri
        enabled: akar.terbuka
        function onTataBerubah() {
            const i = galeri.indeksFoto(akar.foto.id ?? -1)
            if (i < 0) { akar.tutup(); return }
            akar.indeks = i
            strip.positionViewAtIndex(i, ListView.Center)
        }
    }

    Keys.onEscapePressed: keluar()
    Keys.onLeftPressed: geser(-1)
    Keys.onRightPressed: geser(1)
    Keys.onPressed: (e) => {
        if (e.key === Qt.Key_I) infoTerbuka = !infoTerbuka
        else if (e.key === Qt.Key_F) { kotakWajah = !kotakWajah; foto = galeri.foto(indeks) }
        else if (e.key === Qt.Key_0) reset()
        else if (e.key === Qt.Key_Plus || e.key === Qt.Key_Equal) zoomTengah(zoom * 1.4)
        else if (e.key === Qt.Key_Minus) zoomTengah(zoom / 1.4)
    }

    component TombolLayar: Tombol {
        jenis: "ikon"
        warnaIsi: aktif ? Theme.padaAksen : Theme.layarTeks
        warnaSorot: Theme.layarSorot
        warnaTekan: Theme.layarIsi
    }

    Rectangle { anchors.fill: parent; color: Theme.layar; opacity: akar.masuk }
    MouseArea { anchors.fill: parent }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Bilah judul penampil: kembali di kiri, nama di tengah, alat dan tombol jendela di kanan
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiJudul
            opacity: akar.masuk

            TombolLayar {
                id: tKembali
                x: Theme.j8
                anchors.verticalCenter: parent.verticalCenter
                ikon: "kembali"; petunjuk: qsTr("Kembali ke galeri (Esc)"); onDiklik: akar.keluar()
            }
            Teks {
                anchors.centerIn: parent
                width: Math.min(implicitWidth, parent.width * 0.34)
                color: Theme.layarTeks
                peran: "kecil"
                text: akar.foto.nama || ""
            }
            Row {
                anchors.right: parent.right
                height: parent.height
                TombolLayar { id: tWajah; anchors.verticalCenter: parent.verticalCenter; ikon: "wajah"; aktif: akar.kotakWajah; petunjuk: qsTr("Tampilkan kotak wajah (F)"); onDiklik: akar.kotakWajah = !akar.kotakWajah }
                Item { width: Theme.j4; height: 1 }
                TombolLayar { id: tBuka; anchors.verticalCenter: parent.verticalCenter; ikon: "buka"; petunjuk: qsTr("Tampilkan di folder"); mati: !(akar.foto.terhubung ?? false); onDiklik: galeri.tampilkanDiFolder(akar.indeks) }
                Item { width: Theme.j4; height: 1 }
                TombolLayar { id: tInfo; anchors.verticalCenter: parent.verticalCenter; ikon: "info"; aktif: akar.infoTerbuka; petunjuk: qsTr("Rincian foto (I)"); onDiklik: akar.infoTerbuka = !akar.infoTerbuka }
                Item { width: Theme.j12; height: 1 }
                TombolJendela { id: capMin; jenis: "min"; warnaIsi: Theme.layarTeks; warnaSorot: Theme.layarSorot }
                TombolJendela { id: capMaks; jenis: "maks"; warnaIsi: Theme.layarTeks; warnaSorot: Theme.layarSorot }
                TombolJendela { id: capTutup; jenis: "tutup"; warnaIsi: Theme.layarTeks; warnaSorot: Theme.layarSorot }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Item {
                    id: panggung
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: Theme.j16
                    Layout.rightMargin: Theme.j16
                    Layout.topMargin: Theme.j4
                    Layout.bottomMargin: Theme.j4
                    clip: akar.masuk >= 1

                    Item {
                        id: gambar
                        readonly property real rasio: akar.foto.rasio || 1
                        readonly property real lebarTampil: Math.min(panggung.width, panggung.height * rasio)
                        readonly property real tinggiTampil: lebarTampil / rasio
                        readonly property point pusatAsal: panggung.mapFromItem(null, akar.kotakAsal.x + akar.kotakAsal.width / 2, akar.kotakAsal.y + akar.kotakAsal.height / 2)
                        readonly property real skalaAsal: Math.max(akar.kotakAsal.width / Math.max(lebarTampil, 1), akar.kotakAsal.height / Math.max(tinggiTampil, 1))
                        width: lebarTampil
                        height: tinggiTampil
                        x: (panggung.width - width) / 2 + akar.panX + (1 - akar.masuk) * (pusatAsal.x - panggung.width / 2)
                        y: (panggung.height - height) / 2 + akar.panY + (1 - akar.masuk) * (pusatAsal.y - panggung.height / 2)
                        scale: akar.zoom * (skalaAsal + (1 - skalaAsal) * akar.masuk)

                        // Thumbnail kecil sudah di memori: tidak pernah ada bingkai kosong
                        Image {
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            source: akar.terbuka ? galeri.urlKecil(akar.indeks) : ""
                        }
                        Image {
                            id: pratinjau
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            source: akar.foto.pratinjau || ""
                        }
                        Image {
                            id: asli
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            autoTransform: true
                            cache: false
                            sourceSize: Qt.size(2800, 2800)
                            // Foto asli hanya saat diperbesar: menelusuri tidak perlu membangunkan HDD
                            source: akar.zoom > 1.01 ? (akar.foto.asli || "") : ""
                            opacity: status === Image.Ready ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.gerakSedang } }
                        }
                    }

                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton
                        cursorShape: akar.zoom > 1 ? (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor) : Qt.ArrowCursor
                        property real awalX
                        property real awalY
                        onPressed: (m) => { awalX = m.x - akar.panX; awalY = m.y - akar.panY }
                        onPositionChanged: (m) => {
                            if (pressed && akar.zoom > 1) {
                                akar.panX = m.x - awalX
                                akar.panY = m.y - awalY
                                akar.batasi()
                            }
                        }
                        onDoubleClicked: (m) => akar.zoomKe(akar.zoom > 1 ? 1 : 2.5, m.x, m.y)
                        onWheel: (w) => akar.zoomKe(akar.zoom * (w.angleDelta.y > 0 ? 1.2 : 1 / 1.2), w.x, w.y)
                    }

                    // Di atas area geser, supaya kotak wajah bisa diklik
                    Item {
                        x: gambar.x
                        y: gambar.y
                        width: gambar.width
                        height: gambar.height
                        scale: gambar.scale

                        Repeater {
                            model: akar.kotakWajah ? (akar.foto.wajah || []) : []
                            delegate: Rectangle {
                                required property var modelData
                                x: modelData.x1 * gambar.width
                                y: modelData.y1 * gambar.height
                                width: (modelData.x2 - modelData.x1) * gambar.width
                                height: (modelData.y2 - modelData.y1) * gambar.height
                                color: "transparent"
                                radius: Theme.sudutKontrol / akar.zoom
                                border.width: Theme.j2 / akar.zoom
                                border.color: Theme.layarTeks

                                Rectangle {
                                    visible: parent.modelData.nama !== ""
                                    anchors.top: parent.bottom
                                    anchors.topMargin: Theme.j4 / akar.zoom
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: labelNama.implicitWidth + Theme.j12
                                    height: Theme.j24
                                    scale: 1 / akar.zoom
                                    radius: Theme.sudutKontrol
                                    color: Theme.layarPanel
                                    Teks { id: labelNama; anchors.centerIn: parent; peran: "kecil"; color: Theme.layarTeks; text: parent.parent.modelData.nama }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: parent.modelData.orang >= 0 ? akar.bukaOrang(parent.modelData.orang) : akar.bukaMirip(parent.modelData.id)
                                }
                            }
                        }
                    }

                    component Panah: Rectangle {
                        id: panah
                        property string ikon: ""
                        property string petunjuk: ""
                        property bool tampil: false
                        signal diklik()
                        opacity: tampil || tekanPanah.containsMouse ? 1 : 0
                        width: Theme.j40
                        height: Theme.j40
                        radius: width / 2
                        color: tekanPanah.pressed ? Theme.layarIsi : Theme.layarPanel
                        border.width: 1
                        border.color: Theme.layarGaris
                        Accessible.role: Accessible.Button
                        Accessible.name: petunjuk
                        Ikon { anchors.centerIn: parent; nama: panah.ikon; warna: Theme.layarTeks }
                        MouseArea { id: tekanPanah; anchors.fill: parent; hoverEnabled: true; onClicked: panah.diklik() }
                    }

                    // Muncul saat penunjuk ada di tepi; panah keyboard selalu bisa
                    Panah {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        ikon: "kiri"; petunjuk: qsTr("Foto sebelumnya")
                        visible: akar.indeks > 0
                        tampil: area.containsMouse && area.mouseX < Theme.tepiPanah
                        onDiklik: akar.geser(-1)
                    }
                    Panah {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        ikon: "kanan"; petunjuk: qsTr("Foto berikutnya")
                        visible: akar.indeks < galeri.jumlah - 1
                        tampil: area.containsMouse && area.mouseX > panggung.width - Theme.tepiPanah
                        onDiklik: akar.geser(1)
                    }

                    Rectangle {
                        visible: akar.zoom > 1.01 && !(akar.foto.terhubung ?? true)
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: Theme.j12
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: pesanDrive.implicitWidth + Theme.j24
                        height: Theme.tinggiKontrol
                        radius: Theme.sudutKontrol
                        color: Theme.layarPanel
                        Teks {
                            id: pesanDrive
                            anchors.centerIn: parent
                            color: Theme.layarTeks2
                            text: qsTr("Drive foto tidak terpasang. Yang tampil salinan kecilnya.")
                        }
                    }
                }

                // Jajaran foto mengambang
                Item {
                    visible: akar.height >= Theme.minTinggiStrip
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.tinggiStrip
                    opacity: akar.masuk

                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - Theme.j32, galeri.jumlah * (Theme.ubinStrip + Theme.j4) + Theme.j8)
                        height: Theme.ubinStrip + Theme.j12
                        radius: Theme.sudut
                        color: Theme.layarPanel
                        border.width: 1
                        border.color: Theme.layarGaris

                        ListView {
                            id: strip
                            anchors.fill: parent
                            anchors.margins: Theme.j4
                            orientation: ListView.Horizontal
                            model: akar.terbuka ? galeri.jumlah : 0
                            spacing: Theme.j4
                            clip: true
                            currentIndex: akar.indeks
                            boundsBehavior: Flickable.StopAtBounds
                            highlightFollowsCurrentItem: false
                            cacheBuffer: 400

                            delegate: Item {
                                id: kecil
                                required property int index
                                readonly property bool kini: index === akar.indeks
                                width: Theme.ubinStrip
                                height: strip.height
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: Theme.j2
                                    asynchronous: true
                                    fillMode: Image.PreserveAspectCrop
                                    source: galeri.urlKecil(kecil.index)
                                    opacity: kecil.kini ? 1 : 0.7
                                }
                                SudutFoto { anchors.margins: Theme.j2; warna: Theme.layarPanel }
                                Rectangle {
                                    anchors.fill: parent
                                    radius: Theme.sudutFoto + Theme.j2
                                    color: "transparent"
                                    border.width: kecil.kini ? Theme.j2 : 0
                                    border.color: Theme.aksenLayar
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: { akar.indeks = kecil.index; akar.muat() }
                                }
                            }
                        }
                    }
                }

                // Bilah status: format di kiri, zoom di kanan
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.tinggiStatus
                    Layout.leftMargin: Theme.j16
                    Layout.rightMargin: Theme.j12
                    spacing: Theme.j4
                    opacity: akar.masuk

                    Teks { peran: "kecil"; color: Theme.layarTeks2; text: akar.foto.format || "" }
                    Ikon { nama: "gambar"; warna: Theme.layarTeks2; ukuran: Theme.j12; Layout.leftMargin: Theme.j12 }
                    Teks { peran: "kecil"; color: Theme.layarTeks2; text: (akar.foto.dimensi || "") }
                    Item { Layout.fillWidth: true }
                    TombolLayar { ikon: "pas"; petunjuk: qsTr("Pas layar (0)"); mati: akar.zoom <= 1; onDiklik: akar.reset() }
                    Teks {
                        Layout.preferredWidth: Theme.j40 + Theme.j8
                        horizontalAlignment: Text.AlignHCenter
                        peran: "kecil"
                        color: Theme.layarTeks
                        text: Math.round(gambar.lebarTampil * akar.zoom / Math.max(akar.foto.lebar || 1, 1) * 100) + "%"
                    }
                    TombolLayar { ikon: "perkecil"; petunjuk: qsTr("Perkecil (−)"); mati: akar.zoom <= 1; onDiklik: akar.zoomTengah(akar.zoom / 1.4) }
                    Slider {
                        id: geserZoom
                        Layout.preferredWidth: Theme.lebarZoom
                        Layout.preferredHeight: Theme.tinggiKontrol
                        from: 1
                        to: akar.zoomMaks
                        value: akar.zoom
                        onMoved: akar.zoomTengah(value)
                        Accessible.name: qsTr("Perbesaran")
                        focusPolicy: Qt.NoFocus  // panah tetap berpindah foto setelah penggeser dipakai
                        background: Rectangle {
                            x: geserZoom.leftPadding
                            y: (geserZoom.height - height) / 2
                            width: geserZoom.availableWidth
                            height: Theme.j4
                            radius: Theme.j2
                            color: Theme.layarIsi
                            Rectangle { width: geserZoom.visualPosition * parent.width; height: parent.height; radius: Theme.j2; color: Theme.aksenLayar }
                        }
                        handle: Rectangle {
                            x: geserZoom.leftPadding + geserZoom.visualPosition * (geserZoom.availableWidth - width)
                            y: (geserZoom.height - height) / 2
                            width: Theme.j16
                            height: Theme.j16
                            radius: Theme.j8
                            color: Theme.layarPanel
                            border.width: Theme.j4
                            border.color: Theme.aksenLayar
                        }
                    }
                    TombolLayar { ikon: "perbesar"; petunjuk: qsTr("Perbesar (+)"); mati: akar.zoom >= akar.zoomMaks; onDiklik: akar.zoomTengah(akar.zoom * 1.4) }
                }
            }

            // Panel mengambang bertab, seperti panel di penyunting Photos
            Rectangle {
                visible: akar.panelTampil
                Layout.fillHeight: true
                Layout.preferredWidth: Theme.lebarInfo
                Layout.rightMargin: Theme.j12
                Layout.bottomMargin: Theme.j12
                radius: Theme.sudut
                color: Theme.layarPanel
                border.width: 1
                border.color: Theme.layarGaris

                component Tab: Item {
                    id: tb
                    property string kunci: ""
                    property string ikon: ""
                    property string label: ""
                    readonly property bool kini: akar.tab === kunci
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Accessible.role: Accessible.PageTab
                    Accessible.name: label
                    Column {
                        anchors.centerIn: parent
                        spacing: Theme.j4
                        Ikon { anchors.horizontalCenter: parent.horizontalCenter; nama: tb.ikon; warna: tb.kini ? Theme.aksenLayar : Theme.layarTeks }
                        Teks { anchors.horizontalCenter: parent.horizontalCenter; peran: "kecil"; color: tb.kini ? Theme.aksenLayar : Theme.layarTeks; text: tb.label }
                    }
                    Rectangle {
                        visible: tb.kini
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Theme.j24
                        height: Theme.tebalPenanda
                        radius: Theme.j2
                        color: Theme.aksenLayar
                    }
                    MouseArea { anchors.fill: parent; onClicked: akar.tab = tb.kunci }
                }

                component Baris: RowLayout {
                    id: br
                    property string ikon: ""
                    property string isi: ""
                    visible: isi !== ""
                    Layout.fillWidth: true
                    spacing: Theme.j12
                    Ikon { nama: br.ikon; warna: Theme.layarTeks2; Layout.alignment: Qt.AlignTop; Layout.topMargin: Theme.j8 + Theme.j2 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: teksBaris.implicitHeight + Theme.j16
                        radius: Theme.sudutKontrol
                        color: Theme.layarIsi
                        Teks {
                            id: teksBaris
                            x: Theme.j12
                            y: Theme.j8
                            width: parent.width - Theme.j24
                            color: Theme.layarTeks
                            text: br.isi
                            wrapMode: Text.WrapAnywhere
                            elide: Text.ElideNone
                        }
                    }
                }

                RowLayout {
                    id: tabs
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: Theme.tinggiKepala - Theme.j8
                    spacing: 0
                    Tab { kunci: "info"; ikon: "info"; label: qsTr("Info") }
                    Tab { kunci: "orang"; ikon: "orang"; label: qsTr("Orang") }
                }
                Rectangle { anchors.top: tabs.bottom; width: parent.width; height: 1; color: Theme.layarGaris }

                Flickable {
                    anchors.top: tabs.bottom
                    anchors.topMargin: Theme.j16
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    contentHeight: (akar.tab === "info" ? kolomInfo.implicitHeight : kolomOrang.implicitHeight) + Theme.j24
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true
                    ScrollBar.vertical: Gulir {}

                    ColumnLayout {
                        id: kolomInfo
                        visible: akar.tab === "info"
                        x: Theme.j16
                        width: parent.width - Theme.j32
                        spacing: Theme.j8

                        Baris { ikon: "gambar"; isi: akar.foto.nama || "" }
                        Baris { ikon: "kalender"; isi: akar.foto.tanggal ? akar.foto.tanggal + ", " + akar.foto.jam : "" }
                        Teks {
                            visible: akar.foto.tanggalFile ?? false
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.j16 + Theme.j12
                            peran: "kecil"
                            color: Theme.layarTeks2
                            wrapMode: Text.WordWrap
                            text: qsTr("Foto ini tidak menyimpan tanggal pengambilan, jadi yang dipakai tanggal berkasnya.")
                        }
                        Baris { ikon: "folder"; isi: akar.foto.folder || "" }

                        Teks { Layout.topMargin: Theme.j12; color: Theme.layarTeks; font.weight: Font.DemiBold; text: qsTr("Ukuran") }
                        Teks { peran: "kecil"; color: Theme.layarTeks2; text: (akar.foto.ukuran || "") + "     " + (akar.foto.dimensi || "") }

                        Teks { Layout.topMargin: Theme.j12; color: Theme.layarTeks; font.weight: Font.DemiBold; text: qsTr("Sumber") }
                        Teks { peran: "kecil"; color: Theme.layarTeks2; text: (akar.foto.terhubung ?? false) ? qsTr("Foto asli bisa dibuka") : qsTr("Drive foto tidak terpasang") }
                    }

                    ColumnLayout {
                        id: kolomOrang
                        visible: akar.tab === "orang"
                        x: Theme.j16
                        width: parent.width - Theme.j32
                        spacing: Theme.j8

                        Teks {
                            visible: (akar.foto.wajah || []).length === 0
                            Layout.fillWidth: true
                            color: Theme.layarTeks2
                            wrapMode: Text.WordWrap
                            text: qsTr("Belum ada wajah yang dikenali di foto ini.")
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.j4
                            Repeater {
                                model: akar.foto.wajah || []
                                delegate: Item {
                                    required property var modelData
                                    width: Theme.lebarWajahInfo
                                    height: Theme.tinggiWajahInfo
                                    Image {
                                        id: mukaInfo
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        y: Theme.j4
                                        width: Theme.avatarFilter + Theme.j4
                                        height: width
                                        sourceSize: Qt.size(96, 96)
                                        asynchronous: true
                                        source: parent.modelData.url
                                    }
                                    Teks {
                                        anchors.top: mukaInfo.bottom
                                        anchors.topMargin: Theme.j4
                                        width: parent.width
                                        horizontalAlignment: Text.AlignHCenter
                                        peran: "kecil"
                                        color: Theme.layarTeks2
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        text: parent.modelData.nama || qsTr("Siapa ini?")
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: parent.modelData.orang >= 0 ? akar.bukaOrang(parent.modelData.orang) : akar.bukaMirip(parent.modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
