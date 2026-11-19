import os
import threading

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import cadangan, db, ekspor, pipa_wajah


class Alat(QObject):
    berubah = Signal()
    _selesai = Signal(str)
    _maju = Signal(int, int)

    def __init__(self, data, galeri):
        super().__init__()
        self._data, self._galeri = data, galeri
        self._sibuk = False
        self._pesan = ""
        self._kini = self._total = 0
        self._calon = ""
        self._selesai.connect(self._usai)
        self._maju.connect(self._set_maju)

    def _set_maju(self, a, b):
        self._kini, self._total = a, b
        self.berubah.emit()

    def _usai(self, pesan):
        self._sibuk, self._pesan = False, pesan
        self.berubah.emit()

    def _jalankan(self, kerja):
        if self._sibuk:
            return
        self._sibuk, self._pesan, self._kini, self._total = True, "", 0, 0
        self.berubah.emit()

        def bungkus():
            try:
                pesan = kerja()
            except (OSError, ValueError) as e:
                pesan = f"Tidak berhasil: {e}"
            self._selesai.emit(pesan)

        threading.Thread(target=bungkus, daemon=True).start()

    @Property(bool, notify=berubah)
    def sibuk(self):
        return self._sibuk

    @Property(str, notify=berubah)
    def pesan(self):
        return self._pesan

    @Property(int, notify=berubah)
    def kini(self):
        return self._kini

    @Property(int, notify=berubah)
    def total(self):
        return self._total

    @Property(str, notify=berubah)
    def calonPulih(self):
        return self._calon

    @Property(str, constant=True)
    def lokasiData(self):
        return str(self._data)

    @Property(str, constant=True)
    def model(self):
        return pipa_wajah.MODEL

    @Slot(str)
    def ekspor(self, url):
        tujuan = os.path.normpath(QUrl(url).toLocalFile())
        saring = self._galeri._saring

        def kerja():
            c = db.buka(self._data / "library.db")
            try:
                r = ekspor.ekspor(c, saring, tujuan, self._data / "jurnal", lapor=self._maju.emit)
            finally:
                c.close()
            t = f"{r.disalin} foto disalin."
            if r.tak_terhubung:
                t += f" {r.tak_terhubung} dilewati karena drive tidak terhubung."
            if r.gagal:
                t += f" {r.gagal} gagal."
            return t

        self._jalankan(kerja)

    @Slot(str)
    def cadangkan(self, url):
        tujuan = os.path.normpath(QUrl(url).toLocalFile())
        self._jalankan(lambda: f"Cadangan tersimpan di {cadangan.buat(self._data, tujuan)}")

    @Slot(str)
    def pilihPulih(self, url):
        folder = os.path.normpath(QUrl(url).toLocalFile())
        try:
            cadangan.periksa(folder)
            self._calon, self._pesan = folder, ""
        except ValueError as e:
            self._calon, self._pesan = "", str(e)
        self.berubah.emit()

    @Slot()
    def batalPulih(self):
        self._calon = ""
        self.berubah.emit()

    @Slot()
    def pulihkan(self):
        cadangan.jadwalkan(self._data, self._calon)
        self._calon, self._pesan = "", "Tutup lalu buka lagi aplikasi untuk memulihkan cadangan."
        self.berubah.emit()
