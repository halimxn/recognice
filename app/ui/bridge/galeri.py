"""Jendela baris galeri untuk QML: SLOT tetap, tiap baris menempati slot `indeks % SLOT`.

Saat digulir satu baris hanya satu slot berubah, jadi delegasi lain tidak dibangun ulang.
"""
import os
import subprocess
from bisect import bisect_right
from datetime import date, datetime, timezone

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, QRunnable, QThreadPool, Qt, QTimer, QUrl, Signal, Slot

from core import db, layout, library, thumbs
from ui.bridge.orang import _url as url_wajah

SLOT = 48
MARGIN = 700
JARAK = 16
TINGGI_KOLEKSI = 196  # deret kartu pembuka; digambar di Foto.qml
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]
FORMAT_TANPA_ASLI = (".heic", ".heif")  # Qt tidak membaca HEIC; pratinjau 1024 yang tampil


def waktu(detik):
    return datetime.fromtimestamp(min(max(detik, 0), 32503680000), timezone.utc)  # batas tahun 3000


def label_hari(detik):
    t = waktu(detik)
    return f"{HARI[t.weekday()]}, {t.day} {BULAN[t.month - 1]} {t.year}"


def label_tanggal(detik):
    t = waktu(detik)
    return f"{t.day} {BULAN[t.month - 1]} {t.year}"


def ukuran_tampil(bita):
    return f"{bita / 1e6:.1f} MB".replace(".", ",") if bita >= 1e6 else f"{max(bita, 1) / 1e3:.0f} KB"


class Terhubung(QObject):
    """Cek drive di benang latar: HDD yang tertidur tidak boleh menahan antarmuka."""
    berubah = Signal(object)

    def __init__(self, jalur_db):
        super().__init__()
        self.jalur_db = jalur_db

    def cek(self):
        c = db.buka(self.jalur_db)
        hasil = {s[0]: library.akar_sumber(c, s[0]) for s in library.daftar_sumber(c)}
        c.close()
        self.berubah.emit(hasil)


class _Tugas(QRunnable):
    def __init__(self, f):
        super().__init__()
        self.f = f

    def run(self):
        self.f()


class Galeri(QAbstractListModel):
    tataBerubah = Signal()
    geserKe = Signal(int)
    tersambungBerubah = Signal()

    POS_Y, TINGGI, JENIS, LABEL, ISI = range(Qt.ItemDataRole.UserRole + 1, Qt.ItemDataRole.UserRole + 6)

    def __init__(self, jalur_db, akar_thumb, tinggi_baris=200, muat_awal=True):
        super().__init__()
        self._c = db.buka(jalur_db)
        self._dasar = QUrl.fromLocalFile(str(akar_thumb)).toString()
        self._akar_thumb = akar_thumb
        self._foto = []
        self._tata = layout.susun([], 1, 1, 1, 1)
        self._slot = [-1] * SLOT
        self._tanda = [None] * SLOT
        self._lebar = 0
        self._tinggi_baris = tinggi_baris
        self._y = self._h = 0
        self._saring = None
        self._panel = {}  # penghalus dari panel Filter, di atas saringan yang sedang aktif
        self._koleksi = []
        self._kunci_koleksi = None
        self._tunda = not muat_awal  # daftar seluruh foto baru dibaca saat benar-benar dibuka
        self._orang = -1
        self._label = ""
        self._bulan = []
        self._akar = {}
        self._terhubung = Terhubung(jalur_db)
        self._terhubung.berubah.connect(self._set_akar)
        self._cek = QTimer(self, interval=30000, timeout=self.cekDrive)
        self._cek.start()
        self.muatUlang()
        self.cekDrive()

    # --- model
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else SLOT

    def roleNames(self):
        return {self.POS_Y: b"posY", self.TINGGI: b"tinggiSlot", self.JENIS: b"jenis", self.LABEL: b"label",
                self.ISI: b"isi"}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        i = self._slot[index.row()]
        if not 0 <= i < len(self._tata.baris):  # slot lama bisa tertinggal saat jendela tanpa tinggi
            return {self.POS_Y: 0, self.TINGGI: 0, self.JENIS: "", self.LABEL: "", self.ISI: []}.get(role)
        b = self._tata.baris[i]
        if role == self.POS_Y:
            return b.y
        if role == self.TINGGI:
            return b.tinggi
        if role == self.JENIS:
            return b.jenis
        if role == self.LABEL:
            return b.label
        if role == self.ISI:
            return [{"x": s.x, "w": s.w, "indeks": s.indeks, "url": self.urlKecil(s.indeks)} for s in b.isi]
        return None

    # --- properti
    @Property(int, notify=tataBerubah)
    def tinggiTotal(self):
        return self._tata.tinggi_total

    @Property(int, notify=tataBerubah)
    def jumlah(self):
        return len(self._foto)

    @Property(int, notify=tataBerubah)
    def tinggiBaris(self):
        return self._tinggi_baris

    @Property(int, notify=tataBerubah)
    def orangAktif(self):
        return self._orang

    @Property(bool, notify=tataBerubah)
    def adaSaring(self):
        return self._saring is not None

    @Property(str, notify=tataBerubah)
    def labelSaring(self):
        return self._label

    @Property(int, constant=True)
    def jarak(self):
        return JARAK

    @Property(int, constant=True)
    def tinggiKoleksi(self):
        return TINGGI_KOLEKSI

    @Property("QVariantList", notify=tataBerubah)
    def koleksi(self):
        return self._koleksi if self._saring is None and not self._panel else []

    @Property("QVariantMap", notify=tataBerubah)
    def panel(self):
        return self._panel

    @Property(int, notify=tataBerubah)
    def jumlahPanel(self):
        return len(self._panel.keys() - {"salah_satu"})

    @Slot("QVariantMap")
    def aturPanel(self, p):
        self._panel = {k: v for k, v in dict(p).items() if v not in (None, "", 0, [], False)}
        self._y = 0
        self.muatUlang()
        self.geserKe.emit(0)

    @Slot(result="QVariantList")
    def tahunTersedia(self):
        return library.tahun_foto(self._c)

    def _terapkan_saring(self, saring):
        self._saring = saring
        self._panel = {}
        orang_ = (saring or {}).get("orang") or []
        self._orang = int(orang_[0]) if len(orang_) == 1 else -1
        self._label = (saring or {}).get("label", "")
        self._y = 0
        self.muatUlang()
        self.geserKe.emit(0)

    @Slot("QVariantMap")
    def saring(self, saringan):
        self._terapkan_saring(dict(saringan))

    @Slot()
    def pastikanMuat(self):
        if self._tunda:
            self._tunda = False
            self.muatUlang()

    @Slot()
    def hapusSaring(self):
        if self._saring is not None or self._panel:
            self._terapkan_saring(None)

    @Slot(int)
    def saringOrang(self, pid):
        if pid < 0:
            self.hapusSaring()
        elif pid != self._orang or set(self._saring or ()) - {"orang", "label"}:
            b = self._c.execute("SELECT nama FROM person WHERE id=?", (pid,)).fetchone()
            self._terapkan_saring({"orang": [pid], "label": (b[0] if b else "") or "Siapa ini?"})

    # --- tata
    def _susun(self):
        # Satu dinding foto tanpa kepala: tanggal ditunjukkan pil dan linimasa
        foto = [(f.lebar / max(f.tinggi, 1), "") for f in self._foto]
        pembuka = TINGGI_KOLEKSI if self._saring is None and not self._panel and self._koleksi else 0
        self._tata = layout.susun(foto, max(self._lebar, 1), self._tinggi_baris, JARAK, pembuka)
        self._bulan = []
        terakhir = None
        for b in self._tata.baris:
            if b.isi:
                t = waktu(self._foto[b.isi[0].indeks].taken_at)
                if (t.year, t.month) != terakhir:
                    terakhir = (t.year, t.month)
                    self._bulan.append((b.y, f"{BULAN[t.month - 1]} {t.year}", t.year))
        self.tataBerubah.emit()
        self._kabari(self._isi_jendela())

    def _kabari(self, slot):
        for s in slot:
            self.dataChanged.emit(self.index(s), self.index(s))

    def _tanda_baris(self, i):
        b = self._tata.baris[i]
        return b.y, b.tinggi, b.jenis, b.label, tuple((c.indeks, c.x, c.w, self._foto[c.indeks].id) for c in b.isi)

    def _isi_jendela(self):
        """Kembalikan slot yang isinya berubah; yang tidak berubah tidak dibangun ulang."""
        baris = self._tata.baris
        if not self._h:
            return []
        awal = layout.baris_di_y(self._tata, self._y - MARGIN) if baris else 0
        akhir = min(layout.baris_di_y(self._tata, self._y + self._h + MARGIN) + 1, awal + SLOT, len(baris)) if baris else 0
        # Hanya baris dekat layar yang diisi: saat penggulir diseret, tiap slot baru membangun ulang deretan foto.
        # Slot lain dibiarkan memegang baris lamanya selama baris itu masih sama di tata sekarang (di luar layar, gratis).
        ingin = {i % SLOT: i for i in range(awal, akhir)}
        ubah = []
        for s in range(SLOT):
            i = ingin.get(s, self._slot[s])
            tanda = self._tanda_baris(i) if 0 <= i < len(baris) else None
            if s not in ingin and tanda != self._tanda[s]:
                i, tanda = -1, None  # baris lama sudah berubah tempat atau isi: kosongkan, jangan tampil di posisi salah
            if self._slot[s] != i or self._tanda[s] != tanda:
                self._slot[s], self._tanda[s] = i, tanda
                ubah.append(s)
        return ubah

    @Slot(float, float)
    def lihat(self, y, h):
        self._y, self._h = y, h
        self._kabari(self._isi_jendela())

    @Slot(float)
    def atur(self, lebar):
        lebar = int(lebar)
        if lebar != self._lebar and lebar > 0:
            jangkar = self._foto_di_y()
            self._lebar = lebar
            self._susun()
            self._ke_foto(jangkar)

    @Slot(int)
    def aturTinggiBaris(self, t):
        if t != self._tinggi_baris:
            jangkar = self._foto_di_y()
            self._tinggi_baris = t
            self._susun()
            self._ke_foto(jangkar)

    def _foto_di_y(self):
        if self._y <= 0 or not self._foto or not self._tata.baris:
            return None
        i = layout.baris_di_y(self._tata, self._y)
        for b in self._tata.baris[i:i + 3]:
            if b.isi:
                return self._foto[b.isi[0].indeks].id
        return None

    def _ke_foto(self, foto_id):
        if foto_id is None:
            return
        baris = self._tata.baris
        for i, b in enumerate(baris):
            if b.isi and any(self._foto[s.indeks].id == foto_id for s in b.isi):
                self.geserKe.emit(baris[i - 1].y if i and baris[i - 1].jenis == "kepala" else b.y)
                return

    def _segarkan_koleksi(self):
        if self._saring is not None or self._panel:
            return  # kartu pembuka hanya milik Galeri tanpa saringan
        if not self._foto:
            self._koleksi, self._kunci_koleksi = [], None
            return
        h = date.today()
        kunci = (len(self._foto), self._foto[0].id, h)
        if kunci != self._kunci_koleksi:
            self._kunci_koleksi = kunci
            self._koleksi = [{**k, "url": f"{self._dasar}/{k['sha1'][:2]}/{k['sha1']}.{thumbs.KECIL}.jpg"}
                             for k in library.koleksi(self._c, h.year, h.month, h.day)]

    @Slot()
    def muatUlang(self):
        jangkar = self._foto_di_y()
        saring = {**(self._saring or {}), **self._panel}
        if "tahun" in self._panel:  # tahun dari panel menggantikan bulan dari pencarian
            saring.pop("bulan", None)
        self._foto = [] if self._tunda and not saring else library.semua_foto(self._c, saring)
        self._indeks = {f.id: i for i, f in enumerate(self._foto)}
        self._segarkan_koleksi()
        self._susun()
        self._ke_foto(jangkar)

    # --- scrubber
    @Slot(float, result="QVariantList")
    def penanda(self, tinggi_track):
        hasil, tahun, y_akhir = [], None, -99
        total = max(self._tata.tinggi_total, 1)
        for y, _, th in self._bulan:
            if th != tahun:
                tahun = th
                py = y / total * tinggi_track
                if py - y_akhir >= 22:
                    hasil.append({"label": str(th), "frac": y / total})
                    y_akhir = py
        return hasil

    @Slot(float, result="QVariantList")
    def titik(self, tinggi_track):
        """Garis kecil tiap bulan pada linimasa, dijarangkan agar tidak berdempet."""
        hasil, y_akhir = [], -99
        total = max(self._tata.tinggi_total, 1)
        for y, _, _ in self._bulan:
            py = y / total * tinggi_track
            if py - y_akhir >= 10:
                hasil.append(y / total)
                y_akhir = py
        return hasil

    @Slot(float, result=str)
    def tanggalDi(self, y):
        return label_tanggal(self._foto[self.fotoDi(y)].taken_at) if self._foto else ""

    @Slot(float, result=str)
    def bulanDi(self, frac):
        if not self._bulan:
            return ""
        y = frac * self._tata.tinggi_total
        return self._bulan[max(bisect_right([b[0] for b in self._bulan], y) - 1, 0)][1]

    # --- foto
    def _url(self, indeks, ukuran):
        sha = self._foto[indeks].sha1
        return f"{self._dasar}/{sha[:2]}/{sha}.{ukuran}.jpg"

    # --- keyboard
    def _baris_foto(self, i):
        return next((k for k, b in enumerate(self._tata.baris) if b.isi and b.isi[0].indeks <= i <= b.isi[-1].indeks), None)

    @Slot(int, result=int)
    def yFoto(self, i):
        k = self._baris_foto(i)
        return self._tata.baris[k].y if k is not None else 0

    @Slot(float, result=int)
    def fotoDi(self, y):
        baris = self._tata.baris
        k = layout.baris_di_y(self._tata, y) if baris else 0
        return next((b.isi[0].indeks for b in baris[k:] if b.isi), 0)

    @Slot(int, int, result=int)
    def tetangga(self, i, arah):
        """Foto di baris atas (-1) atau bawah (+1) yang paling lurus dengan foto `i`."""
        baris, k = self._tata.baris, self._baris_foto(i)
        if k is None:
            return i
        sel = next(s for s in baris[k].isi if s.indeks == i)
        tengah = sel.x + sel.w / 2
        k += arah
        while 0 <= k < len(baris) and not baris[k].isi:
            k += arah
        if not 0 <= k < len(baris):
            return i
        return min(baris[k].isi, key=lambda s: abs(s.x + s.w / 2 - tengah)).indeks

    @Slot(int, result=int)
    def indeksFoto(self, foto_id):
        return self._indeks.get(foto_id, -1)

    @Slot(int, result=str)
    def urlKecil(self, indeks):
        return self._url(indeks, thumbs.KECIL)

    def _set_akar(self, akar):
        if akar != self._akar:
            self._akar = akar
            self.tersambungBerubah.emit()

    @Slot()
    def cekDrive(self):
        QThreadPool.globalInstance().start(_Tugas(self._terhubung.cek))

    @Property("QVariantMap", notify=tersambungBerubah)
    def tersambung(self):
        return {str(k): v is not None for k, v in self._akar.items()}

    def _jalur_asli(self, f):
        akar = self._akar.get(f.source_id)
        return os.path.join(akar, f.jalur_rel.replace("/", "\\")) if akar else None

    @Slot(int, result="QVariantMap")
    def foto(self, i):
        if not 0 <= i < len(self._foto):
            return {}
        f = self._foto[i]
        t = waktu(f.taken_at)
        asli = self._jalur_asli(f)
        nama = f.jalur_rel.rsplit("/", 1)[-1]
        return {
            "id": f.id,
            "pratinjau": self._url(i, thumbs.BESAR),
            "asli": QUrl.fromLocalFile(asli).toString() if asli and not nama.lower().endswith(FORMAT_TANPA_ASLI) else "",
            "terhubung": asli is not None,
            "rasio": f.lebar / max(f.tinggi, 1),
            "lebar": f.lebar,
            "format": nama.rsplit(".", 1)[-1].upper(),
            "nama": nama,
            "folder": f.jalur_rel.rsplit("/", 1)[0] if "/" in f.jalur_rel else "",
            "tanggal": label_hari(f.taken_at),
            "jam": f"{t.hour:02d}.{t.minute:02d}",
            "ukuran": ukuran_tampil(f.ukuran),
            "dimensi": f"{f.lebar} x {f.tinggi}",
            "wajah": [{"id": i_, "x1": a, "y1": b, "x2": c, "y2": d, "orang": p if p is not None else -1, "nama": n or "",
                       "url": url_wajah({"sha1": f.sha1, "x1": a, "y1": b, "x2": c, "y2": d})}
                      for i_, a, b, c, d, p, n in self._c.execute(
                          "SELECT f.id, f.x1, f.y1, f.x2, f.y2, f.person_id, p.nama FROM face f "
                          "LEFT JOIN person p ON p.id=f.person_id WHERE f.photo_id=?", (f.id,))],
            "tanggalFile": self._c.execute("SELECT sumber_tanggal FROM photo WHERE id=?", (f.id,)).fetchone()[0] != "exif",
        }

    @Slot(int)
    def tampilkanDiFolder(self, i):
        if not 0 <= i < len(self._foto):
            return
        asli = self._jalur_asli(self._foto[i])
        if asli and os.path.exists(asli):
            subprocess.Popen(["explorer", "/select,", asli])
