import QtQuick
import "../theme"

// Pilihan berbentuk pil: filter dan pengaturan
Rectangle {
    id: pil
    property string teks: ""
    property bool aktif: false
    signal dipilih()

    width: label.implicitWidth + Theme.j24
    height: Theme.tinggiKontrol - Theme.j8
    radius: height / 2
    color: aktif ? Theme.aksenIsi : area.pressed ? Theme.sorotKuat : area.containsMouse ? Theme.sorot : "transparent"
    border.width: aktif ? 0 : 1
    border.color: activeFocus ? Theme.fokus : Theme.garis
    activeFocusOnTab: true
    Accessible.role: Accessible.RadioButton
    Accessible.name: teks
    Accessible.checked: aktif
    Keys.onSpacePressed: dipilih()
    Keys.onReturnPressed: dipilih()

    Teks {
        id: label
        anchors.centerIn: parent
        text: pil.teks
        color: pil.aktif ? Theme.padaAksen : Theme.teks2
        font.weight: pil.aktif ? Font.DemiBold : Font.Normal
    }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: pil.dipilih() }
}
