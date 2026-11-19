import QtQuick
import QtQuick.Controls
import "../theme"

// Bilah gulir tipis gaya Windows 11: muncul saat menggulir atau disorot
ScrollBar {
    id: bilah
    policy: ScrollBar.AsNeeded
    implicitWidth: Theme.j8
    padding: Theme.j2
    contentItem: Rectangle {
        implicitWidth: bilah.hovered || bilah.pressed ? Theme.j4 : Theme.j2
        radius: width / 2
        color: Theme.teks2
        opacity: bilah.active ? 0.7 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.gerakSedang } }
    }
    background: Item {}
}
