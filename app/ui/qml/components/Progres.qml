import QtQuick
import "../theme"

Rectangle {
    property real nilai: 0
    height: 3
    radius: height / 2
    color: Theme.sorot
    Rectangle {
        height: parent.height
        radius: height / 2
        color: Theme.aksen
        width: parent.width * Math.max(0, Math.min(1, parent.nilai))
    }
}
