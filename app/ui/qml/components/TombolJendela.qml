import QtQuick
import "../theme"

// Tombol jendela gaya Windows 11. "maks" diklik lewat Windows agar menu Snap Layouts muncul.
Rectangle {
    id: t
    property string jenis: "min"  // min | maks | tutup
    property color warnaIsi: Theme.teksCangkang
    property color warnaSorot: Theme.cangkangSorot
    readonly property bool maksimal: Window.window && Window.window.visibility === Window.Maximized
    readonly property bool disorot: area.containsMouse || (jenis === "maks" && bingkai.maksDisorot)
    readonly property bool ditekan: area.pressed || (jenis === "maks" && bingkai.maksDitekan)

    width: Theme.lebarTombolJendela
    height: Theme.tinggiJudul
    color: !disorot ? "transparent" : jenis === "tutup" ? (ditekan ? "#b2271a" : "#c42b1c") : warnaSorot
    Accessible.role: Accessible.Button
    Accessible.name: jenis === "min" ? qsTr("Perkecil jendela") : jenis === "tutup" ? qsTr("Tutup") : maksimal ? qsTr("Pulihkan") : qsTr("Perbesar jendela")

    Ikon {
        anchors.centerIn: parent
        ukuran: 10
        nama: t.jenis === "min" ? "minimal" : t.jenis === "tutup" ? "tutupJendela" : t.maksimal ? "pulihkan" : "maksimal"
        warna: t.jenis === "tutup" && t.disorot ? "#ffffff" : t.warnaIsi
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {
            const w = Window.window
            if (t.jenis === "min") w.showMinimized()
            else if (t.jenis === "tutup") w.close()
            else bingkai.alihMaksimal()
        }
    }
}
