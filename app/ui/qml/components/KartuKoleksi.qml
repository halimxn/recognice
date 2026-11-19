import QtQuick
import QtQuick.Layouts
import "../theme"

// Kartu seperti deretan koleksi di Photos: judul di atas foto, keterangan dan "Lihat" di bawahnya
Rectangle {
    id: kartu
    property string url: ""
    property var urls: []  // tiga foto terbaru: kolase bila kartu cukup lebar
    property string judul: ""
    property string info: ""
    property bool terfokus: false
    signal diklik()
    readonly property bool kolase: urls.length >= 3 && width >= Theme.lebarKolaseMin

    color: area.containsMouse ? Theme.sorot : Theme.permukaan
    Accessible.role: Accessible.Button
    Accessible.name: judul

    Rectangle {
        id: sampul
        width: parent.width
        height: parent.height - Theme.j40
        color: kartu.kolase ? Theme.permukaan : Theme.sorot
        Image {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: kartu.kolase ? Math.round(parent.width * 2 / 3) - Theme.j2 : parent.width
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
            source: kartu.url
        }
        Column {
            visible: kartu.kolase
            anchors.right: parent.right
            width: Math.round(parent.width / 3)
            height: parent.height
            spacing: Theme.j2
            Repeater {
                model: kartu.kolase ? kartu.urls.slice(1, 3) : []
                delegate: Image {
                    required property string modelData
                    width: parent.width
                    height: (parent.height - Theme.j2) / 2
                    asynchronous: true
                    fillMode: Image.PreserveAspectCrop
                    source: modelData
                }
            }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: Theme.j40 + Theme.j16
            gradient: Gradient {
                GradientStop { position: 0; color: "#00000000" }
                GradientStop { position: 1; color: "#aa000000" }
            }
        }
        Teks {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Theme.j12
            anchors.bottomMargin: Theme.j8
            font.pixelSize: Theme.ukKartu
            color: "#ffffff"
            text: kartu.judul
        }
    }
    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.j12
        anchors.rightMargin: Theme.j12
        height: Theme.j40
        Teks { peran: "kecil"; color: Theme.teks2; text: kartu.info; Layout.fillWidth: true }
        Teks { peran: "kecil"; color: Theme.aksenTeks; text: qsTr("Lihat") }
    }
    SudutFoto {}
    Rectangle {
        anchors.fill: parent
        radius: Theme.sudutFoto
        color: "transparent"
        border.width: kartu.terfokus ? Theme.j2 : 0
        border.color: Theme.fokus
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: kartu.diklik()
    }
}
