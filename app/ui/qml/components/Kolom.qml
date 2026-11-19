import QtQuick
import QtQuick.Controls
import "../theme"

// Kolom teks gaya Windows 11: garis aksen di bawah saat aktif
TextField {
    id: kolom
    implicitHeight: Theme.tinggiKolom
    color: Theme.teks
    placeholderTextColor: Theme.teks2
    selectionColor: Theme.aksen
    selectedTextColor: Theme.padaAksen
    font.family: Theme.huruf
    font.pixelSize: Theme.ukTeks
    leftPadding: Theme.j12
    rightPadding: Theme.j12
    renderType: Text.NativeRendering
    verticalAlignment: Text.AlignVCenter
    background: Rectangle {
        radius: Theme.sudutKontrol
        color: kolom.hovered && !kolom.activeFocus ? Theme.sorot : Theme.permukaan
        border.width: 1
        border.color: Theme.garis
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: kolom.activeFocus ? Theme.j2 : 1
            color: kolom.activeFocus ? Theme.aksen : Theme.teks2
        }
    }
}
