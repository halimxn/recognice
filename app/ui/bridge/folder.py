from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import db, layout, library, thumbs

BATAS_DINDING = 60
TINGGI_BARIS = 170
JARAK = 16


class Folder(QObject):
    """Menjelajah per folder. Seluruhnya dari database dan thumbnail, tanpa menyentuh drive foto."""
    berubah = Signal()
    dindingBerubah = Signal()

    def __init__(self, jalur_db, akar_thumb, muat=True):
        """`muat=False`: pohon folder baru dibaca saat `segarkan` (halaman Folder dibuka), bukan saat aplikasi mulai."""
        super().__init__()
        self._c = db.buka(jalur_db)
        self._dasar = QUrl.fromLocalFile(str(akar_thumb)).toString()
        self._kini = None  # (source, rel); None = akar
        self._lebar = 0
        self._dinding, self._tinggi_dinding, self._foto = [], 0, []
        self._pohon, self._label, self._anak = {}, {}, []
        if muat:
            self.segarkan()

    def _url(self, sha):
        return f"{self._dasar}/{sha[:2]}/{sha}.{thumbs.KECIL}.jpg"

    def _tile(self, kunci, nama):
        n = self._pohon[kunci]
        return {"source": kunci[0], "rel": kunci[1], "nama": nama, "jumlah": n["jumlah"], "punyaAnak": bool(n["anak"]),
                "subfolder": len(n["anak"]), "url": self._url(n["sha1"]), "urls": [self._url(s) for s in n["sampul"]]}

    def _isi(self, source, rel):
        return [self._tile((source, a), a.rsplit("/", 1)[-1]) for a in sorted(self._pohon[source, rel]["anak"], key=str.casefold)]

    @Slot()
    def segarkan(self):
        self._pohon = library.pohon_folder(self._c)
        self._label = {b[0]: b[1] for b in library.daftar_sumber(self._c)}
        if self._kini is not None and self._kini not in self._pohon:
            self._kini = None
        self._hitung()

    def _hitung(self):
        akar = [k for k in self._pohon if k[1] == ""]
        if self._kini is not None:
            self._anak = self._isi(*self._kini)
        elif len(akar) == 1:
            self._anak = self._isi(*akar[0])
        else:
            self._anak = [self._tile(k, self._label.get(k[0], "")) for k in sorted(akar)]
        self.berubah.emit()
        saring = None if self._kini is None else {"folder": {"source": self._kini[0], "rel": self._kini[1]}}
        self._foto = library.foto_terbaru(self._c, saring, BATAS_DINDING)
        self._susun_dinding()

    def _susun_dinding(self):
        self._dinding, self._tinggi_dinding = [], 0
        if self._lebar > 0 and self._foto:
            tata = layout.susun([(f.lebar / max(f.tinggi, 1), "") for f in self._foto], self._lebar, TINGGI_BARIS, JARAK, 0)
            baris = [b for b in tata.baris if b.isi]
            if len(baris) > 1 and baris[-1].isi[-1].x + baris[-1].isi[-1].w < self._lebar:
                baris.pop()  # baris terakhir yang tidak penuh terlihat seperti sisa
            self._dinding = [{"x": s.x, "y": b.y, "w": s.w, "h": b.tinggi - JARAK, "url": self._url(self._foto[s.indeks].sha1),
                              "id": self._foto[s.indeks].id} for b in baris for s in b.isi]
            self._tinggi_dinding = baris[-1].y + baris[-1].tinggi - JARAK
        self.dindingBerubah.emit()

    @Slot(float)
    def atur(self, lebar):
        if int(lebar) != self._lebar:
            self._lebar = int(lebar)
            self._susun_dinding()

    @Property("QVariantList", notify=dindingBerubah)
    def dinding(self):
        return self._dinding

    @Property(int, notify=dindingBerubah)
    def tinggiDinding(self):
        return self._tinggi_dinding

    @Property(str, notify=berubah)
    def judulDinding(self):
        return "Foto terbaru" if self._kini is None else "Foto di folder ini"

    @Slot(result="QVariantMap")
    def saringanDinding(self):
        return {"foto": [d["id"] for d in self._dinding], "label": self.judulDinding}

    @Property("QVariantList", notify=berubah)
    def anak(self):
        return self._anak

    @Property(bool, notify=berubah)
    def dalam(self):
        return self._kini is not None

    @Property(str, notify=berubah)
    def judul(self):
        if self._kini is None:
            return ""
        return self._kini[1].rsplit("/", 1)[-1] or self._label.get(self._kini[0], "")

    @Property(int, notify=berubah)
    def jumlah(self):
        if self._kini is not None:
            return self._pohon[self._kini]["jumlah"]
        return sum(n["jumlah"] for k, n in self._pohon.items() if k[1] == "")

    @Property("QVariantList", notify=berubah)
    def jejak(self):
        if self._kini is None:
            return []
        s, rel = self._kini
        bagian = rel.split("/") if rel else []
        return [{"nama": n, "source": s, "rel": "/".join(bagian[:i + 1])} for i, n in enumerate(bagian)]

    @Slot()
    def keAkar(self):
        self._kini = None
        self._hitung()

    @Slot(int, str)
    def masuk(self, source, rel):
        if (source, rel) in self._pohon:
            self._kini = (source, rel)
            self._hitung()

    @Slot()
    def naik(self):
        if self._kini is None:
            return
        s, rel = self._kini
        induk = rel.rsplit("/", 1)[0] if "/" in rel else ""
        satu_sumber = sum(1 for k in self._pohon if k[1] == "") == 1
        self._kini = None if (rel == "" or (induk == "" and satu_sumber)) else (s, induk)
        self._hitung()

    @Slot(result="QVariantMap")
    def saringanIni(self):
        s, rel = self._kini
        return {"folder": {"source": s, "rel": rel}, "label": self.judul}

    @Slot(int, str, str, result="QVariantMap")
    def saringanUntuk(self, source, rel, nama):
        return {"folder": {"source": source, "rel": rel}, "label": nama}
