import QtQuick
import QtQuick.Window

Window {
    id: w
    width: 1280
    height: 800
    visible: true
    color: "#0f1113"
    title: "Recognice bench"

    property var waktu: []

    function foto(nama) { g.grabToImage(function (r) { r.saveToFile(keluar + "/" + nama + ".png") }) }

    function ambil(nama) {
        lapor.fase(nama, JSON.stringify(waktu))
        waktu = []
    }

    GridView {
        id: g
        anchors.fill: parent
        cellWidth: 212
        cellHeight: 212
        model: 20000
        cacheBuffer: 600
        reuseItems: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: Item {
            required property int index
            width: g.cellWidth
            height: g.cellHeight
            Rectangle { anchors.fill: parent; anchors.margins: 2; color: "#1d2125" }
            Image {
                anchors.fill: parent
                anchors.margins: 2
                asynchronous: true
                fillMode: Image.PreserveAspectCrop
                sourceSize: Qt.size(256, 256)
                source: akarThumb + "/" + (index % 256).toString(16).padStart(2, "0") + "/" + index + ".jpg"
            }
        }
    }

    FrameAnimation {
        id: fa
        running: false
        onTriggered: w.waktu.push(Date.now())
    }

    SequentialAnimation {
        id: urutan
        ScriptAction { script: fa.running = true }
        PauseAnimation { duration: 3000 }
        ScriptAction { script: w.ambil("diam") }
        NumberAnimation { target: g; property: "contentY"; from: 0; to: 30000; duration: 15000 }
        ScriptAction { script: { w.foto("gulir"); w.ambil("gulir") } }
        NumberAnimation { target: g; property: "contentY"; from: 30000; to: 330000; duration: 10000 }
        ScriptAction { script: w.ambil("scrub") }
        PauseAnimation { duration: 1500 }
        ScriptAction { script: { w.foto("mendarat"); w.ambil("mendarat"); fa.running = false; lapor.selesai() } }
    }

    Timer { interval: 1500; running: true; onTriggered: urutan.start() }
}
