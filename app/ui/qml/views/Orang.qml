import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: akar
    objectName: "orangHalaman"
    property string halaman: "daftar"   // daftar | tinjau | wajah
    signal bukaFotoOrang(int id)

    function kelolaWajah(id) { orang.bukaWajah(id); halaman = "wajah" }
    function mulaiTinjau() { orang.mulaiTinjau(); halaman = "tinjau"; kolomNama.bersihkan() }
    // Orang tanpa nama: klik langsung membuka halaman beri nama, mulai dari orang itu
    function buka(o) { if (o.nama) bukaFotoOrang(o.id); else { orang.mulaiTinjauDari(o.id); halaman = "tinjau"; kolomNama.bersihkan() } }
    onHalamanChanged: if (halaman === "daftar") orang.selesaiTinjau()
    Connections {
        target: orang
        function onDaftarAkanBerubah() { kisi.posisi = kisi.contentY }
        function onDaftarBerubah() { Qt.callLater(() => { kisi.contentY = kisi.posisi }) }
        function onWajahAkanBerubah() { kisiWajah.posisi = kisiWajah.contentY }
    }

    function angka(n) { return n.toLocaleString(Qt.locale("id_ID"), "f", 0) }

    // --- Daftar orang
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        spacing: 0
        visible: akar.halaman === "daftar" && orang.daftar.length > 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiKepala
            Teks { peran: "judul"; text: qsTr("Orang") }
            Item { Layout.fillWidth: true }
            Teks { visible: orang.sedang; color: Theme.teks2; text: qsTr("Mengelompokkan wajah…") }
            Tombol {
                visible: !orang.sedang
                jenis: "ikon"; ikon: "ulang"; petunjuk: qsTr("Kelompokkan ulang wajah")
                onDiklik: orang.perbarui()
            }
        }

        Kartu {
            visible: orang.jumlahTinjau > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.j40 + Theme.j16
            Layout.bottomMargin: Theme.j12
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j16
                anchors.rightMargin: Theme.j12
                spacing: Theme.j12
                Ikon { nama: "info"; warna: Theme.aksen }
                Teks {
                    Layout.fillWidth: true
                    text: qsTr("%1 orang belum diberi nama. Beri nama supaya mudah dicari.").arg(akar.angka(orang.jumlahTinjau))
                }
                Tombol { teks: qsTr("Beri nama"); jenis: "utama"; onDiklik: akar.mulaiTinjau() }
            }
        }

        GridView {
            id: kisi
            property real posisi: 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: orang.daftar
            cellWidth: width > 0 ? width / Math.max(1, Math.floor(width / Theme.selOrang)) : Theme.selOrang
            cellHeight: Theme.avatarOrang + Theme.teksOrang
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Gulir {}
            cacheBuffer: 400
            activeFocusOnTab: true
            Accessible.name: qsTr("Daftar orang")
            Keys.onReturnPressed: if (currentItem) akar.buka(currentItem.modelData)
            Keys.onSpacePressed: if (currentItem) akar.buka(currentItem.modelData)

            delegate: Item {
                id: sel
                required property var modelData
                width: kisi.cellWidth
                height: kisi.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Theme.j4
                    radius: Theme.sudut
                    color: area.containsMouse ? Theme.sorot : "transparent"
                    border.width: kisi.activeFocus && sel.GridView.isCurrentItem ? Theme.j2 : 0
                    border.color: Theme.fokus
                }
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: Theme.j12
                    spacing: Theme.j8
                    width: parent.width - Theme.j24
                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Theme.avatarOrang; height: Theme.avatarOrang
                        sourceSize: Qt.size(192, 192)
                        asynchronous: true
                        source: sel.modelData.url
                    }
                    Column {
                        width: parent.width
                        Teks {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            font.weight: Font.DemiBold
                            color: sel.modelData.nama ? Theme.teks : Theme.teks2
                            text: sel.modelData.nama || qsTr("Siapa ini?")
                        }
                        Teks {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            peran: "kecil"
                            color: Theme.teks2
                            text: qsTr("%1 foto").arg(akar.angka(sel.modelData.jumlah))
                        }
                    }
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: akar.buka(sel.modelData)
                }
            }
        }

        Teks { visible: orang.pesan !== ""; color: Theme.bahaya; text: orang.pesan; Layout.fillWidth: true }
    }

    KeadaanKosong {
        anchors.centerIn: parent
        visible: akar.halaman === "daftar" && orang.daftar.length === 0
        ikon: "orang"
        judul: orang.sedang ? qsTr("Mengelompokkan wajah…") : qsTr("Belum ada orang")
        keterangan: orang.sedang ? qsTr("Sebentar lagi muncul di sini.")
            : qsTr("Orang muncul di sini setelah wajah di foto Anda dikenali. Itu berjalan sendiri selama aplikasi terbuka.")
    }

    // --- Tinjau: satu kelompok per layar, seluruhnya dengan keyboard
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        anchors.bottomMargin: Theme.j16
        spacing: Theme.j12
        visible: akar.halaman === "tinjau"

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiKepala
            spacing: Theme.j8
            Tombol { jenis: "ikon"; ikon: "kembali"; petunjuk: qsTr("Kembali"); onDiklik: akar.halaman = "daftar" }
            Teks { peran: "besar"; text: qsTr("Beri nama") }
            Item { Layout.fillWidth: true }
            Teks {
                visible: !(orang.tinjau.selesai ?? true)
                color: Theme.teks2
                text: qsTr("Orang ke-%1 dari %2 · %3 foto").arg(akar.angka(orang.tinjau.urutan || 0)).arg(akar.angka(orang.tinjau.total || 0))
                      .arg(akar.angka(orang.tinjau.jumlah || 0))
            }
            Tombol {
                visible: !(orang.tinjau.selesai ?? true)
                teks: qsTr("Lihat semua fotonya"); ikon: "galeri"
                onDiklik: akar.bukaFotoOrang(orang.tinjau.id)
            }
        }

        KeadaanKosong {
            visible: orang.tinjau.selesai ?? false
            Layout.alignment: Qt.AlignCenter
            Layout.fillHeight: true
            ikon: "orang"
            judul: qsTr("Semua orang sudah diberi nama")
            keterangan: qsTr("Kalau ada wajah baru, orangnya muncul lagi di sini.")
        }

        Flow {
            visible: !(orang.tinjau.selesai ?? true)
            Layout.fillWidth: true
            Layout.fillHeight: false
            spacing: Theme.j12
            clip: true
            Repeater {
                model: orang.tinjau.wajah || []
                delegate: Image {
                    required property string modelData
                    width: Theme.wajahTinjau; height: Theme.wajahTinjau
                    sourceSize: Qt.size(192, 192)
                    asynchronous: true
                    source: modelData
                }
            }
        }

        // Saran gabung
        Kartu {
            visible: !(orang.tinjau.selesai ?? true) && !!orang.tinjau.saran
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.tinggiSaran
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j12
                anchors.rightMargin: Theme.j12
                spacing: Theme.j12
                Image {
                    Layout.preferredWidth: Theme.avatarFilter; Layout.preferredHeight: Theme.avatarFilter
                    sourceSize: Qt.size(96, 96)
                    asynchronous: true
                    source: orang.tinjau.saran ? orang.tinjau.saran.url : ""
                }
                Teks {
                    Layout.fillWidth: true
                    text: orang.tinjau.saran
                        ? qsTr("Mungkin orang yang sama dengan %1 (%2)").arg(orang.tinjau.saran.nama || qsTr("orang lain")).arg(orang.tinjau.saran.pita.toLowerCase())
                        : ""
                }
                Tombol { teks: qsTr("Ya, orang yang sama"); onDiklik: { orang.gabungSaran(); kolomNama.bersihkan() } }
            }
        }

        RowLayout {
            visible: !(orang.tinjau.selesai ?? true)
            Layout.fillWidth: true
            spacing: Theme.j12

            Kolom {
                id: kolomNama
                Layout.preferredWidth: Theme.lebarKolomNama
                placeholderText: qsTr("Siapa ini? Ketik namanya")
                focus: akar.halaman === "tinjau"
                property var serupa: []
                property int pilih: -1
                onTextEdited: { serupa = orang.namaSerupa(text); pilih = -1 }
                function bersihkan() { text = ""; serupa = []; pilih = -1; forceActiveFocus() }
                function simpan() {
                    const n = pilih >= 0 ? serupa[pilih] : text
                    if (n.trim() !== "") { orang.simpanNama(n); bersihkan() }
                }
                Keys.onReturnPressed: simpan()
                Keys.onEnterPressed: simpan()
                Keys.onTabPressed: { orang.lewati(); bersihkan() }
                Keys.onEscapePressed: akar.halaman = "daftar"
                Keys.onDownPressed: pilih = Math.min(pilih + 1, serupa.length - 1)
                Keys.onUpPressed: pilih = Math.max(pilih - 1, -1)
                Keys.onPressed: (e) => {
                    if (!(e.modifiers & Qt.ControlModifier)) return
                    if (e.key === Qt.Key_G) { if (orang.tinjau.saran) { orang.gabungSaran(); bersihkan() } e.accepted = true }
                    else if (e.key === Qt.Key_H) { orang.sembunyikanKini(); bersihkan(); e.accepted = true }
                    else if (e.key === Qt.Key_P) { akar.kelolaWajah(orang.tinjau.id); e.accepted = true }
                }

                Kartu {
                    visible: kolomNama.serupa.length > 0 && kolomNama.activeFocus
                    anchors.left: parent.left
                    anchors.bottom: parent.top
                    anchors.bottomMargin: Theme.j4
                    width: parent.width
                    height: kolomSerupa.implicitHeight + Theme.j8
                    Column {
                        id: kolomSerupa
                        anchors.fill: parent
                        anchors.margins: Theme.j4
                        Repeater {
                            model: kolomNama.serupa
                            delegate: Rectangle {
                                required property string modelData
                                required property int index
                                width: parent.width
                                height: Theme.tinggiKontrol
                                radius: Theme.sudutKontrol
                                color: kolomNama.pilih === index ? Theme.sorotKuat : "transparent"
                                Teks { anchors.verticalCenter: parent.verticalCenter; x: Theme.j8; text: parent.modelData }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: { kolomNama.text = parent.modelData; kolomNama.pilih = -1; kolomNama.simpan() }
                                }
                            }
                        }
                    }
                }
            }

            Tombol { teks: qsTr("Simpan"); jenis: "utama"; onDiklik: kolomNama.simpan() }
            Tombol { teks: qsTr("Lewati"); onDiklik: { orang.lewati(); kolomNama.bersihkan() } }
            Tombol { teks: qsTr("Sembunyikan"); petunjuk: qsTr("Bukan orang yang perlu dicari, misalnya orang lewat"); onDiklik: { orang.sembunyikanKini(); kolomNama.bersihkan() } }
            Item { Layout.fillWidth: true }
            Teks {
                peran: "kecil"
                color: Theme.teks2
                horizontalAlignment: Text.AlignRight
                text: qsTr("Tab: lewati · Ctrl+G: orang yang sama · Ctrl+H: sembunyikan · Ctrl+P: periksa wajahnya")
            }
        }
        Item { Layout.fillHeight: true }  // isian dan tombol tetap dekat wajah-wajahnya
    }

    // --- Kelola wajah satu orang
    ColumnLayout {
        id: halamanWajah
        anchors.fill: parent
        anchors.leftMargin: Theme.tepiIsi
        anchors.rightMargin: Theme.j24
        anchors.bottomMargin: Theme.j16
        spacing: Theme.j8
        visible: akar.halaman === "wajah"
        property var terpilih: ({})
        readonly property int jumlahTerpilih: Object.keys(terpilih).length
        function alih(id) {
            const t = Object.assign({}, terpilih)
            if (t[id]) delete t[id]; else t[id] = true
            terpilih = t
        }
        function idTerpilih() { return Object.keys(terpilih).map(Number) }

        Connections {
            target: orang
            function onWajahBerubah() {
                halamanWajah.terpilih = ({})
                Qt.callLater(() => { kisiWajah.contentY = kisiWajah.posisi })
                if (akar.halaman === "wajah" && !orang.wajahOrang.id) akar.halaman = "daftar"
                kolomGanti.text = orang.wajahOrang.nama || ""
            }
        }

        RowLayout {
            Layout.preferredHeight: Theme.tinggiKepala
            spacing: Theme.j8
            Tombol { jenis: "ikon"; ikon: "kembali"; petunjuk: qsTr("Kembali"); onDiklik: akar.halaman = "daftar" }
            Kolom {
                id: kolomGanti
                Layout.preferredWidth: Theme.lebarKolomGanti
                placeholderText: qsTr("Siapa ini?")
                font.weight: Font.DemiBold
                Accessible.name: qsTr("Nama orang")
                onAccepted: { orang.gantiNama(text); focus = false }
            }
            Teks { color: Theme.teks2; text: qsTr("%1 foto").arg(akar.angka(orang.wajahOrang.jumlah || 0)) }
        }

        Teks { color: Theme.teks2; text: qsTr("Ada wajah yang bukan orang ini? Pilih wajahnya, lalu tekan Bukan dia.") }

        GridView {
            id: kisiWajah
            property real posisi: 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: orang.wajahOrang.wajah || []
            cellWidth: Theme.selKelola
            cellHeight: Theme.selKelola
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Gulir {}
            cacheBuffer: 400
            delegate: Item {
                id: wj
                required property var modelData
                readonly property bool dipilih: !!halamanWajah.terpilih[modelData.id]
                width: kisiWajah.cellWidth
                height: kisiWajah.cellHeight
                Image {
                    anchors.centerIn: parent
                    width: Theme.wajahKelola; height: Theme.wajahKelola
                    sourceSize: Qt.size(192, 192)
                    asynchronous: true
                    source: wj.modelData.url
                    opacity: wj.dipilih ? 0.55 : 1
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: Theme.cincinKelola; height: Theme.cincinKelola
                    radius: width / 2
                    color: "transparent"
                    border.width: wj.dipilih ? Theme.tebalPenanda : hover.containsMouse ? Theme.j2 : 0
                    border.color: wj.dipilih ? Theme.aksen : Theme.teks2
                }
                Rectangle {
                    visible: wj.dipilih
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.j12
                    y: Theme.j8
                    width: Theme.tandaPilih; height: Theme.tandaPilih; radius: width / 2
                    color: Theme.aksen
                    Ikon { anchors.centerIn: parent; ukuran: Theme.j12; nama: "centang"; warna: Theme.padaAksen }
                }
                MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; onClicked: halamanWajah.alih(wj.modelData.id) }
            }
        }

        Kartu {
            visible: halamanWajah.jumlahTerpilih > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.j40 + Theme.j12
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.j16
                anchors.rightMargin: Theme.j12
                spacing: Theme.j8
                Teks { font.weight: Font.DemiBold; text: qsTr("%1 wajah dipilih").arg(halamanWajah.jumlahTerpilih); Layout.fillWidth: true }
                Tombol { teks: qsTr("Batal pilih"); onDiklik: halamanWajah.terpilih = ({}) }
                Tombol { teks: qsTr("Pisahkan jadi orang lain"); onDiklik: orang.pisahkan(halamanWajah.idTerpilih(), "") }
                Tombol { teks: qsTr("Bukan dia"); jenis: "utama"; onDiklik: orang.bukanDia(halamanWajah.idTerpilih()) }
            }
        }
    }
}
