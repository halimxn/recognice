import QtQuick
import "../theme"

Text {
    property string peran: "teks"  // judul | besar | sedang | teks | kecil

    color: peran === "judul" ? Theme.teksJudul : Theme.teks
    font.family: peran === "judul" || peran === "besar" ? Theme.hurufJudul : Theme.huruf
    font.pixelSize: peran === "judul" ? Theme.ukJudul : peran === "besar" ? Theme.ukBesar : peran === "sedang" ? Theme.ukSedang
                  : peran === "kecil" ? Theme.ukKecil : Theme.ukTeks
    font.weight: peran === "judul" ? Font.Bold : peran === "besar" ? Font.DemiBold : Font.Normal
    lineHeightMode: Text.FixedHeight
    lineHeight: peran === "judul" ? Theme.barisJudul : peran === "besar" ? Theme.barisBesar : peran === "sedang" ? Theme.barisSedang
              : peran === "kecil" ? Theme.barisKecil : Theme.barisTeks
    renderType: Text.NativeRendering
    verticalAlignment: Text.AlignVCenter
    elide: Text.ElideRight
}
