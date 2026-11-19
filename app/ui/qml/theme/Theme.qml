pragma Singleton
import QtQuick

QtObject {
    // gelap | terang | auto (ikuti Windows)
    property string tema: "auto"
    readonly property bool gelap: tema === "gelap" || (tema === "auto" && Qt.styleHints.colorScheme === Qt.Dark)
    function pilih(g, t) { return gelap ? g : t }

    // Windows 10 tidak punya Segoe UI Variable dan Segoe Fluent Icons
    readonly property var _keluarga: Qt.fontFamilies()
    readonly property string huruf: _keluarga.indexOf("Segoe UI Variable Text") >= 0 ? "Segoe UI Variable Text" : "Segoe UI"
    readonly property string hurufJudul: _keluarga.indexOf("Segoe UI Variable Display") >= 0 ? "Segoe UI Variable Display" : "Segoe UI"
    readonly property string hurufIkon: _keluarga.indexOf("Segoe Fluent Icons") >= 0 ? "Segoe Fluent Icons" : "Segoe MDL2 Assets"

    readonly property color kanvas: pilih("#0a0a0a", "#f3f3f3")
    readonly property color permukaan: pilih("#1f1f1f", "#fbfbfb")
    readonly property color isi: pilih("#1f1f1f", "#ffffff")
    readonly property color padaIsi: pilih("#e6e6e6", "#1a1a1a")
    readonly property color isiSorot: pilih("#2c2c2c", "#e9e9e9")
    readonly property color isiTekan: pilih("#363636", "#dedede")
    readonly property color sorot: pilih("#2c2c2c", "#e9e9e9")
    readonly property color sorotKuat: pilih("#363636", "#dedede")
    readonly property color garis: pilih("#333333", "#e0e0e0")
    readonly property color teks: pilih("#e6e6e6", "#1a1a1a")
    readonly property color teks2: pilih("#a6a6a6", "#5c5c5c")
    readonly property color teks3: pilih("#999999", "#666666")
    readonly property color teksJudul: pilih("#ffffff", "#111111")
    readonly property color fokus: pilih("#ffffff", "#1a1a1a")
    readonly property color bahaya: pilih("#ff99a4", "#c42b1c")
    readonly property color tirai: pilih("#99000000", "#66000000")

    // Bilah judul dan rel; pada tema gelap dan terang menyatu dengan kanvas
    readonly property color cangkang: pilih("#0a0a0a", "#f3f3f3")
    readonly property color cangkangIsi: pilih("#1f1f1f", "#ffffff")
    readonly property color cangkangSorot: pilih("#2c2c2c", "#e9e9e9")
    readonly property color teksCangkang: pilih("#e6e6e6", "#1a1a1a")
    readonly property color teksCangkang2: pilih("#999999", "#666666")

    property color aksenGelap: "#60cdff"
    property color aksenTerang: "#005fb8"
    property color isiAksenGelap: "#0067c0"
    property color isiAksenTerang: "#005fb8"
    property color padaAksenGelap: "#ffffff"
    property color padaAksenTerang: "#ffffff"
    readonly property color aksen: gelap ? aksenGelap : aksenTerang
    readonly property color aksenIsi: gelap ? isiAksenGelap : isiAksenTerang
    readonly property color padaAksen: gelap ? padaAksenGelap : padaAksenTerang
    readonly property color aksenTeks: aksen

    // Penampil selalu gelap: foto dinilai di latar yang tidak mewarnai
    readonly property color layar: "#1a1e2a"
    readonly property color layarTeks: "#ffffff"
    readonly property color layarTeks2: "#a8adb8"
    readonly property color layarPanel: "#2b2d30"
    readonly property color layarGaris: "#3d3f44"
    readonly property color layarSorot: "#22ffffff"  // format Qt: #AARRGGBB
    readonly property color layarIsi: "#35373c"
    readonly property color aksenLayar: aksenGelap

    readonly property int j2: 2
    readonly property int j4: 4
    readonly property int j8: 8
    readonly property int j12: 12
    readonly property int j16: 16
    readonly property int j24: 24
    readonly property int j32: 32
    readonly property int j40: 40

    readonly property int tinggiJudul: 48
    readonly property int lebarTombolJendela: 46
    readonly property int lebarRel: 48
    readonly property int tepiIsi: 12
    readonly property int tinggiButirRel: 38
    readonly property int tinggiKepala: 72
    readonly property int tinggiKontrol: 36
    readonly property int tinggiKolom: 36
    readonly property int tinggiCari: 32
    readonly property int lebarCari: 336
    readonly property int lebarScrubber: 52
    readonly property int lebarFilter: 288
    readonly property int lebarInfo: 288
    readonly property int tinggiStrip: 72
    readonly property int tinggiStatus: 40
    readonly property int minTinggiStrip: 560
    readonly property int minLebarInfo: 960
    readonly property int ubinStrip: 48
    readonly property int sudut: 12
    readonly property int sudutKontrol: 4
    readonly property int sudutFoto: 10
    readonly property int folderSumber: 56
    readonly property int tinggiSaringUkuran: 40
    readonly property int avatarFilter: 44
    readonly property int avatarOrang: 112
    readonly property int lebarSelFolder: 300
    readonly property int lebarKolaseMin: 240
    readonly property int tinggiSampulMaks: 240

    readonly property int ikonRel: 15
    readonly property int tebalPenanda: 3
    readonly property int lebarJudulMaks: 420
    readonly property int batasSempit: 1050
    readonly property int batasPenampil: 860
    readonly property int tepiPanah: 140
    readonly property int ruangSampingStrip: 220
    readonly property int lebarZoom: 120
    readonly property int lebarWajahInfo: 68
    readonly property int tinggiWajahInfo: 88
    readonly property int kotakCentang: 20
    readonly property int selOrang: 152
    readonly property int teksOrang: 72
    readonly property int lebarKolomNama: 360
    readonly property int lebarKolomGanti: 240
    readonly property int wajahTinjau: 128
    readonly property int tinggiSaran: 64
    readonly property int selKelola: 112
    readonly property int wajahKelola: 96
    readonly property int cincinKelola: 100
    readonly property int tandaPilih: 22
    readonly property int wajahKecil: 64
    readonly property int wajahHasil: 88
    readonly property int lebarOrangHasil: 96
    readonly property int tinggiOrangHasil: 116
    readonly property int selHasilLebar: 104
    readonly property int selHasilTinggi: 124
    readonly property int zonaSeret: 136
    readonly property int zonaRingkas: 64
    readonly property int barisSumber: 76
    readonly property int barisSumberAktif: 108
    readonly property int kartuWajah: 84
    readonly property int lebarDialog: 440
    readonly property int lebarSakelar: 40
    readonly property int tinggiSakelar: 20
    readonly property int bulatSakelar: 12

    // Diukur dari tinggi huruf tangkapan Photos pada lebar jendela yang sama
    readonly property int ukKecil: 11
    readonly property int ukTeks: 13
    readonly property int ukSedang: 15
    readonly property int ukKartu: 16
    readonly property int ukBesar: 20
    readonly property int ukJudul: 42
    readonly property int barisKecil: 14
    readonly property int barisTeks: 18
    readonly property int barisSedang: 20
    readonly property int barisBesar: 28
    readonly property int barisJudul: 54

    readonly property int gerakCepat: 83
    readonly property int gerakSedang: 167
    readonly property int gerakMasuk: 220

    // Satu petunjuk untuk seluruh aplikasi; digambar di Main.qml
    property Item sasaranPetunjuk: null
    property string teksPetunjuk: ""
    function tunjuk(sasaran, teks) { sasaranPetunjuk = sasaran; teksPetunjuk = teks }
    function lepas(sasaran) { if (sasaranPetunjuk === sasaran) sasaranPetunjuk = null }
}
