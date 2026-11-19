import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "theme"
import "components"
import "views"

ApplicationWindow {
    id: jendela
    width: Math.min(1280, Screen.desktopAvailableWidth)
    height: Math.min(800, Screen.desktopAvailableHeight - 40)
    minimumWidth: 720
    minimumHeight: 480
    flags: Qt.Window | Qt.FramelessWindowHint
    visible: false  // ditampilkan Python setelah gaya jendela dipasang
    title: lightbox.terbuka && lightbox.foto.nama ? lightbox.foto.nama + " - Recognice" : "Recognice"
    color: Theme.cangkang

    // Folder 0, Galeri 1, Orang 2, Cari 3, Sumber 4, Pengaturan 5
    property int menuAktif: 1
    readonly property var menuAtas: [
        { t: qsTr("Cari dengan foto"), i: "cariFoto", m: 3 },
        { t: qsTr("Galeri"), i: "galeri", m: 1 },
        { t: qsTr("Orang"), i: "orang", m: 2 },
        { t: qsTr("Folder"), i: "folder", m: 0 },
        { t: qsTr("Lokasi foto"), i: "sumber", m: 4 }
    ]
    readonly property var menuBawah: [{ t: qsTr("Pengaturan"), i: "atur", m: 5 }]

    Binding { target: Theme; property: "tema"; value: pengaturan.tema }
    Component.onCompleted: {
        const a = pengaturan.aksen
        Theme.aksenGelap = a.gelap
        Theme.aksenTerang = a.terang
        Theme.isiAksenGelap = a.isi_gelap
        Theme.isiAksenTerang = a.isi_terang
        Theme.padaAksenGelap = a.pada_gelap
        Theme.padaAksenTerang = a.pada_terang
        if (pengaturan.halamanAwal === "folder") menuAktif = 0
    }

    // Halaman selain Galeri baru dibuat saat pertama dibuka, lalu dipertahankan: jendela pertama tampil lebih cepat
    component Halaman: Loader {
        required property int no
        readonly property bool tampil: jendela.menuAktif === no
        active: false
        onTampilChanged: if (tampil) active = true
        Component.onCompleted: if (tampil) active = true
    }
    // Setelah bingkai pertama tampil, supaya jendela muncul lebih dulu
    Timer { interval: 60; running: true; onTriggered: if (jendela.menuAktif === 1) galeri.pastikanMuat() }

    property int asalSaring: 2
    function pilihMenu(i) {
        if (kotakCari.terbuka) kotakCari.tutup()
        galeri.hapusSaring()
        if (i === 1) galeri.pastikanMuat()
        menuAktif = i
        if (i === 2) halamanOrang.item.halaman = "daftar"
    }
    function bukaFotoOrang(id, asal) { asalSaring = asal === undefined ? 2 : asal; galeri.saringOrang(id); menuAktif = 1 }
    function lihatHasil(saringan, asal) { asalSaring = asal; galeri.saring(saringan); menuAktif = 1 }
    // Foto yang dibuka dari dinding Folder: menutup penampil kembali ke Folder, bukan ke Galeri
    property bool dariDinding: false
    function bukaDariFolder(saringan, id) { lihatHasil(saringan, 0); dariDinding = true; lightbox.buka(galeri.indeksFoto(id)) }

    function angka(n) { return n.toLocaleString(Qt.locale("id_ID"), "f", 0) }

    // Dipanggil dari bingkai.py untuk titik di bilah judul: mana yang kontrol, sisanya untuk menggeser jendela
    function kontrolDi(x, y) {
        const dalam = (b) => {
            if (!b.visible) return false
            const p = b.mapToItem(null, 0, 0)
            return x >= p.x && x < p.x + b.width && y >= p.y && y < p.y + b.height
        }
        if (dalam(lightbox.terbuka ? lightbox.tombolMaks : tMaks)) return "maks"
        return (lightbox.terbuka ? lightbox.kontrolJudul : [kotakCari, tMin, tTutup]).some(dalam) ? "kontrol" : ""
    }

    readonly property string statusPindai: !pindai.aktif ? ""
        : pindai.karenaBaterai ? qsTr("Berhenti: laptop tidak dicas")
        : pindai.dijeda ? qsTr("Dijeda")
        : pindai.tahap === "wajah" ? qsTr("Mengenali wajah %1 / %2").arg(angka(pindai.kini)).arg(angka(pindai.total))
        : pindai.total > 0 ? qsTr("Membaca foto %1 / %2").arg(angka(pindai.kini)).arg(angka(pindai.total))
        : qsTr("Mencari foto…")

    FolderDialog {
        id: pilihFolder
        title: qsTr("Pilih folder foto")
        onAccepted: { pindai.tambah(selectedFolder.toString()); jendela.pilihMenu(4) }
    }
    FolderDialog {
        id: pilihLokasi
        property int sumber: -1
        title: qsTr("Di mana folder foto ini sekarang?")
        onAccepted: pindai.pindahkan(sumber, selectedFolder.toString())
    }
    Shortcut { sequence: "Ctrl+F"; enabled: !lightbox.terbuka && kotakCari.visible; onActivated: kotakCari.fokus() }

    component ButirRel: Item {
        id: butir
        required property var modelData
        readonly property bool aktif: jendela.menuAktif === modelData.m
        property string petunjuk: modelData.t
        property bool lencana: false
        implicitWidth: Theme.lebarRel
        implicitHeight: Theme.tinggiButirRel
        activeFocusOnTab: true
        Accessible.role: Accessible.PageTab
        Accessible.name: modelData.t
        Keys.onSpacePressed: jendela.pilihMenu(modelData.m)
        Keys.onReturnPressed: jendela.pilihMenu(modelData.m)

        Rectangle {
            anchors.centerIn: parent
            width: Theme.j40
            height: Theme.j40
            radius: Theme.sudutKontrol
            color: area.pressed ? Theme.cangkangIsi : area.containsMouse ? Theme.cangkangSorot : "transparent"
            border.width: butir.activeFocus ? Theme.j2 : 0
            border.color: Theme.teksCangkang
        }
        Rectangle {
            visible: butir.aktif
            x: Theme.j4
            anchors.verticalCenter: parent.verticalCenter
            width: Theme.tebalPenanda
            height: Theme.j16
            radius: Theme.j2
            color: Theme.aksen
        }
        Ikon {
            anchors.centerIn: parent
            nama: butir.modelData.i
            ukuran: Theme.ikonRel
            warna: butir.aktif ? Theme.aksen : area.containsMouse ? Theme.teksCangkang : Theme.teksCangkang2
        }
        Rectangle {
            visible: butir.lencana
            x: parent.width / 2 + Theme.j8
            y: Theme.j8
            width: Theme.j8
            height: Theme.j8
            radius: Theme.j4
            color: Theme.aksen
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            onClicked: jendela.pilihMenu(butir.modelData.m)
            onContainsMouseChanged: if (containsMouse) Theme.tunjuk(butir, butir.petunjuk); else Theme.lepas(butir)
        }
    }

    // Kanvas isi bersudut kiri atas di dalam bingkai hitam (tema Krem); tak terlihat bila warnanya sama
    Item {
        x: Theme.lebarRel
        y: Theme.tinggiJudul
        width: parent.width - x
        height: parent.height - y
        Rectangle { anchors.fill: parent; radius: Theme.sudut; color: Theme.kanvas }
        Rectangle { x: Theme.sudut; width: parent.width - x; height: parent.height; color: Theme.kanvas }
        Rectangle { y: Theme.sudut; width: Theme.sudut; height: parent.height - y; color: Theme.kanvas }
    }

    // Isi di bawah bilah judul
    RowLayout {
        anchors.fill: parent
        anchors.topMargin: Theme.tinggiJudul
        spacing: 0
        enabled: !lightbox.terbuka  // Tab tidak boleh tersesat ke halaman di balik penampil

        ColumnLayout {
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.lebarRel
            spacing: 0
            Item { Layout.preferredHeight: Theme.j12 }
            Repeater {
                model: jendela.menuAtas
                delegate: ButirRel {
                    lencana: modelData.m === 4 && pindai.aktif
                    petunjuk: modelData.m === 4 && pindai.aktif ? jendela.statusPindai : modelData.t
                }
            }
            Item { Layout.fillHeight: true }
            Repeater { model: jendela.menuBawah; delegate: ButirRel {} }
            Item { Layout.preferredHeight: Theme.j12 }
        }

        Item {
            id: wadah
            Layout.fillWidth: true
            Layout.fillHeight: true

            StackLayout {
                anchors.fill: parent
                currentIndex: jendela.menuAktif

                Halaman {
                    no: 0
                    sourceComponent: Component {
                        Folder {
                            onLihat: (s) => jendela.lihatHasil(s, 0)
                            onTambahFolder: pilihFolder.open()
                            onBukaFoto: (s, id) => jendela.bukaDariFolder(s, id)
                            onSemuaFoto: jendela.pilihMenu(1)
                        }
                    }
                }
                Foto {
                    id: halamanGaleri
                    onBukaFoto: (i, kotak) => lightbox.buka(i, kotak)
                    onBukaKoleksi: (s) => jendela.lihatHasil(s, 1)
                    onTambahFolder: pilihFolder.open()
                    onKembali: jendela.pilihMenu(jendela.asalSaring)
                    onKelolaWajah: (id) => { galeri.hapusSaring(); jendela.menuAktif = 2; halamanOrang.item.kelolaWajah(id) }
                }
                Halaman {
                    id: halamanOrang
                    no: 2
                    sourceComponent: Component {
                        Orang { onBukaFotoOrang: (id) => jendela.bukaFotoOrang(id) }
                    }
                }
                Halaman {
                    no: 3
                    sourceComponent: Component {
                        Cari {
                            onLihatFoto: (s) => jendela.lihatHasil(s, 3)
                            onBukaOrang: (id) => jendela.bukaFotoOrang(id, 3)
                            onBukaFotoHasil: (s, photoId) => { jendela.lihatHasil(s, 3); lightbox.buka(galeri.indeksFoto(photoId)) }
                        }
                    }
                }
                Halaman {
                    no: 4
                    sourceComponent: Component {
                        Sumber {
                            onTambahFolder: pilihFolder.open()
                            onCariLokasi: (id) => { pilihLokasi.sumber = id; pilihLokasi.open() }
                        }
                    }
                }
                Halaman { no: 5; sourceComponent: Component { Pengaturan {} } }
            }

            // Pekerjaan latar selalu terlihat, tanpa merebut ruang foto
            Rectangle {
                visible: pindai.aktif
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Theme.j2
                color: "transparent"
                Rectangle {
                    height: parent.height
                    color: Theme.aksen
                    width: parent.width * (pindai.total > 0 ? pindai.kini / pindai.total : 0)
                }
            }
        }
    }

    // Klik di luar menutup saran; klik tetap sampai ke tujuannya
    MouseArea {
        anchors.fill: parent
        z: 5
        visible: kotakCari.terbuka
        onPressed: (m) => { kotakCari.tutup(); m.accepted = false }
    }

    // Bilah judul: bagian kosongnya menggeser jendela lewat Windows (bingkai.py)
    Item {
        id: bilahJudul
        z: 10
        width: parent.width
        height: Theme.tinggiJudul
        enabled: !lightbox.terbuka

        Rectangle { anchors.fill: parent; color: Theme.cangkang }
        Image {
            x: (Theme.lebarRel - width) / 2
            anchors.verticalCenter: parent.verticalCenter
            width: Theme.ikonRel
            height: Theme.ikonRel
            sourceSize: Qt.size(40, 40)
            source: "ikon.svg"
        }
        Teks {
            x: Theme.lebarRel + Theme.tepiIsi
            anchors.verticalCenter: parent.verticalCenter
            peran: "kecil"
            color: Theme.teksCangkang2
            text: "Recognice"
        }

        KotakCari {
            id: kotakCari
            // Tinjau seluruhnya memakai keyboard; kotak cari hanya akan merebut fokusnya
            visible: !(jendela.menuAktif === 2 && halamanOrang.item && halamanOrang.item.halaman === "tinjau")
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(Theme.lebarCari, parent.width * 0.34)
            x: (parent.width - width) / 2
            readonly property int asal: jendela.menuAktif === 1 && galeri.adaSaring ? jendela.asalSaring : jendela.menuAktif
            onPilihOrang: (id) => jendela.bukaFotoOrang(id, asal)
            onPilihSaringan: (s) => jendela.lihatHasil(s, asal)
            onCariFoto: jendela.pilihMenu(3)
        }

        Row {
            anchors.right: parent.right
            TombolJendela { id: tMin; jenis: "min" }
            TombolJendela { id: tMaks; jenis: "maks" }
            TombolJendela { id: tTutup; jenis: "tutup" }
        }
    }

    Lightbox {
        id: lightbox
        z: 20
        anchors.fill: parent
        onTerbukaChanged: {
            if (terbuka) return
            halamanGaleri.kembalikanFokus()
            if (jendela.dariDinding) { jendela.dariDinding = false; Qt.callLater(jendela.pilihMenu, 0) }  // jangan mengubah galeri di tengah sinyal ini
        }
        onBukaOrang: (id) => { lightbox.tutup(); jendela.bukaFotoOrang(id, galeri.adaSaring ? jendela.asalSaring : 1) }
        onBukaMirip: (faceId) => { lightbox.tutup(); galeri.hapusSaring(); cari.dariWajah(faceId); jendela.menuAktif = 3 }
    }

    // Petunjuk tunggal untuk semua tombol ikon
    Rectangle {
        id: petunjuk
        z: 100
        property point letak: Qt.point(0, 0)
        property bool tampil: false
        visible: tampil && Theme.sasaranPetunjuk !== null
        x: letak.x
        y: letak.y
        width: teksPetunjuk.implicitWidth + Theme.j16
        height: teksPetunjuk.implicitHeight + Theme.j8 + Theme.j2
        radius: Theme.sudutKontrol
        color: Theme.permukaan
        border.width: 1
        border.color: Theme.garis
        Teks { id: teksPetunjuk; anchors.centerIn: parent; peran: "kecil"; text: Theme.teksPetunjuk }

        Timer { id: tundaPetunjuk; interval: 450; onTriggered: petunjuk.posisikan() }
        function posisikan() {
            const s = Theme.sasaranPetunjuk
            if (!s) return
            const p = s.mapToItem(null, 0, 0)
            const diRel = p.x < Theme.lebarRel
            const x = diRel ? p.x + s.width + Theme.j4 : p.x + (s.width - width) / 2
            const bawahMuat = p.y + s.height + height + Theme.j8 < jendela.height
            const y = diRel ? p.y + (s.height - height) / 2 : bawahMuat ? p.y + s.height + Theme.j4 : p.y - height - Theme.j4
            letak = Qt.point(Math.max(Theme.j4, Math.min(x, jendela.width - width - Theme.j4)), y)
            tampil = true
        }
        Connections {
            target: Theme
            function onSasaranPetunjukChanged() { petunjuk.tampil = false; if (Theme.sasaranPetunjuk) tundaPetunjuk.restart(); else tundaPetunjuk.stop() }
        }
    }
}
