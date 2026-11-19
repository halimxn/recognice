import QtQuick
import "../theme"

// jenis: utama | polos | ikon. `aktif` menandai tombol alih yang sedang menyala.
FocusScope {
    id: akar
    property string teks: ""
    property string ikon: ""
    property string jenis: "polos"
    property bool mati: false
    property bool aktif: false
    property bool latar: false  // tombol ikon bulat berisi, seperti di sebelah Filter
    readonly property bool berisi: jenis === "polos" || latar  // berlatar `isi`: hitam pada tema Krem
    property color warnaIsi: jenis === "utama" ? Theme.padaAksen
        : aktif ? (jenis === "ikon" ? Theme.padaAksen : Theme.aksen) : berisi ? Theme.padaIsi : Theme.teks
    property color warnaSorot: berisi ? Theme.isiSorot : Theme.sorot
    property color warnaTekan: berisi ? Theme.isiTekan : Theme.sorotKuat
    property string petunjuk: ""
    signal diklik()

    implicitHeight: Theme.tinggiKontrol
    implicitWidth: jenis === "ikon" ? Theme.tinggiKontrol : isi.implicitWidth + Theme.j32
    activeFocusOnTab: !mati
    opacity: mati ? 0.45 : 1
    Accessible.role: Accessible.Button
    Accessible.name: teks !== "" ? teks : petunjuk
    Keys.onSpacePressed: if (!mati) diklik()
    Keys.onReturnPressed: if (!mati) diklik()

    Rectangle {
        anchors.fill: parent
        radius: akar.jenis === "ikon" && !akar.latar ? Theme.sudutKontrol : height / 2
        color: akar.jenis === "utama" ? (area.pressed ? Qt.alpha(Theme.aksenIsi, 0.8) : area.containsMouse ? Qt.alpha(Theme.aksenIsi, 0.9) : Theme.aksenIsi)
             : akar.jenis === "ikon" && akar.aktif ? Theme.aksenIsi
             : area.pressed ? akar.warnaTekan : area.containsMouse ? akar.warnaSorot
             : akar.jenis === "ikon" && !akar.latar ? "transparent" : Theme.isi
        border.width: akar.jenis === "polos" ? 1 : 0
        border.color: akar.aktif ? Theme.aksen : Theme.garis
        Behavior on color { ColorAnimation { duration: Theme.gerakCepat } }
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: -Theme.j2
        radius: akar.jenis === "ikon" && !akar.latar ? Theme.sudutKontrol + Theme.j2 : height / 2
        color: "transparent"
        border.width: Theme.j2
        border.color: Theme.fokus
        visible: akar.activeFocus
    }

    Row {
        id: isi
        anchors.centerIn: parent
        spacing: Theme.j8
        Ikon { nama: akar.ikon; warna: akar.warnaIsi; visible: akar.ikon !== ""; anchors.verticalCenter: parent.verticalCenter }
        Teks {
            text: akar.teks
            visible: text !== ""
            color: akar.warnaIsi
            font.weight: akar.jenis === "utama" ? Font.DemiBold : Font.Normal
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: !akar.mati
        onClicked: akar.diklik()
        onContainsMouseChanged: {
            if (akar.petunjuk === "") return
            if (containsMouse) Theme.tunjuk(akar, akar.petunjuk); else Theme.lepas(akar)
        }
    }
    Component.onDestruction: Theme.lepas(akar)
}
