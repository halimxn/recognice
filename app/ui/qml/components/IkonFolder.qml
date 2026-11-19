import QtQuick

// Map kuning seperti di File Explorer, untuk pilihan sumber foto
Image {
    sourceSize: Qt.size(width * 2, height * 2)
    source: "data:image/svg+xml;utf8," + encodeURIComponent(
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 40'>"
        + "<path d='M4 4h14l5 5h21a4 4 0 0 1 4 4v23a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4Z' fill='#d9a23c'/>"
        + "<path d='M0 15a4 4 0 0 1 4-4h40a4 4 0 0 1 4 4v21a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4Z' fill='#f6c85f'/></svg>")
}
