import QtQuick
import "../theme"

// Menutup keempat sudut dengan warna latar. Jauh lebih ringan di HD 520 daripada topeng per foto:
// semua ubin memakai satu tekstur dan digambar dalam satu batch.
BorderImage {
    property color warna: Theme.kanvas
    readonly property int r: Theme.sudutFoto

    anchors.fill: parent
    border { left: r + 2; right: r + 2; top: r + 2; bottom: r + 2 }
    source: "data:image/svg+xml;utf8," + encodeURIComponent(
        "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'><path fill-rule='evenodd' fill='" + warna + "' d='"
        + "M0 0H32V32H0Z M" + r + " 0H" + (32 - r) + "A" + r + " " + r + " 0 0 1 32 " + r + "V" + (32 - r)
        + "A" + r + " " + r + " 0 0 1 " + (32 - r) + " 32H" + r + "A" + r + " " + r + " 0 0 1 0 " + (32 - r)
        + "V" + r + "A" + r + " " + r + " 0 0 1 " + r + " 0Z'/></svg>")
}
