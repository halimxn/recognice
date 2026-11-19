import threading
import time

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from core import daya, db, library, pipa_wajah, scanner

JEDA_MUAT = 30.0  # detik antar-penyegaran galeri selama memindai


class Pindai(QObject):
    berubah = Signal()
    sumberBerubah = Signal()
    perluMuatUlang = Signal()
    _selesai = Signal(object)
    _selesai_wajah = Signal(object)
    _maju = Signal(int, int)
    _maju_wajah = Signal(int, int)
    _lokasi_dicek = Signal(int, str, object)
    perluKelompok = Signal()

    def __init__(self, jalur_db, akar_thumb, galeri, pekerja=3, model=None, jeda_baterai=lambda: True):
        """`model` = (detektor, pengenal, benang); None mematikan tahap wajah."""
        super().__init__()
        self._model = model
        self._jeda_baterai = jeda_baterai
        self._tahap = ""
        self._db, self._thumb, self._galeri, self._pekerja = jalur_db, akar_thumb, galeri, pekerja
        self._c = db.buka(jalur_db)
        self._aktif = False
        self._kini, self._total = 0, 0
        self._sumber_aktif = -1
        self._antrean = []
        self._dijeda_pemakai = self._baterai = False
        self._pesan = ""
        self._batal = threading.Event()
        self._muat_terakhir = 0.0
        self._kelompok_terakhir = 0
        self._dijeda_terakhir = None
        self._mencari_lokasi = False
        self._lokasi_dicek.connect(self._usai_cek_lokasi)
        self._selesai.connect(self._usai)
        self._selesai_wajah.connect(self._usai_wajah)
        if model:
            QTimer.singleShot(3000, self.lanjutkanWajah)  # setelah galeri tampil
        self._maju.connect(self._set_maju)
        self._maju_wajah.connect(self._set_maju_wajah)
        self.perluMuatUlang.connect(galeri.muatUlang)

    @Property(bool, notify=berubah)
    def aktif(self):
        return self._aktif

    @Property(bool, notify=berubah)
    def dijeda(self):
        return self._dijeda_pemakai or self._baterai

    @Property(bool, notify=berubah)
    def karenaBaterai(self):
        return self._baterai and not self._dijeda_pemakai

    @Property(str, notify=berubah)
    def tahap(self):
        return self._tahap

    @Property(int, notify=berubah)
    def kini(self):
        return self._kini

    @Property(int, notify=berubah)
    def total(self):
        return self._total

    @Property(int, notify=berubah)
    def sumberAktif(self):
        return self._sumber_aktif

    @Property(str, notify=berubah)
    def pesan(self):
        return self._pesan

    @Property("QVariantList", notify=sumberBerubah)
    def sumber(self):
        hasil = []
        for id_, label, huruf, rel, kapan, ok, gagal, hilang in library.daftar_sumber(self._c):
            hasil.append({"id": id_, "label": label, "jalur": f"{huruf}\\{rel}", "kapan": kapan or 0, "ok": ok,
                          "gagal": gagal, "hilang": hilang})
        return hasil

    @Slot(str)
    def tambah(self, url):
        akar = QUrl(url).toLocalFile()
        if akar and not self._mencari_lokasi:
            self.pindai(library.tambah_sumber(self._c, akar))
            self.sumberBerubah.emit()

    @Property(int, notify=berubah)
    def wajahTotal(self):
        return self._c.execute("SELECT count(*) FROM photo WHERE status='ok' AND sha1 IS NOT NULL").fetchone()[0]

    @Property(int, notify=berubah)
    def wajahSelesai(self):
        return self._c.execute("SELECT count(*) FROM photo WHERE status='ok' AND sha1 IS NOT NULL AND wajah_model=?",
                               (pipa_wajah.MODEL,)).fetchone()[0]

    @Property(bool, notify=berubah)
    def mencariLokasi(self):
        return self._mencari_lokasi

    @Slot(int, str)
    def pindahkan(self, source_id, url):
        """Arahkan sumber ke folder baru. Ditolak bila folder itu tidak memuat satu pun foto sumber ini."""
        akar = QUrl(url).toLocalFile()
        if not akar or self._aktif or self._mencari_lokasi:
            return
        self._mencari_lokasi, self._pesan = True, "Memeriksa folder…"
        self.berubah.emit()

        def kerja():
            c = db.buka(self._db)
            try:
                hasil = scanner.cocok_lokasi(c, source_id, akar)
            except Exception as e:  # folder tidak terbaca
                hasil = e
            c.close()
            self._lokasi_dicek.emit(source_id, akar, hasil)

        threading.Thread(target=kerja, daemon=True).start()

    def _usai_cek_lokasi(self, source_id, akar, hasil):
        self._mencari_lokasi = False
        punya = self._c.execute("SELECT count(*) FROM photo WHERE source_id=? AND status!='gagal'", (source_id,)).fetchone()[0]
        ada = self._c.execute("SELECT 1 FROM source WHERE id=?", (source_id,)).fetchone()
        if not ada or self._aktif:  # keadaan berubah selama folder diperiksa
            self._pesan = "Lokasi belum diganti karena masih ada pekerjaan lain berjalan, atau folder ini sudah dihapus dari daftar."
        elif isinstance(hasil, Exception):
            self._pesan = f"Folder tidak bisa dibaca: {hasil}"
        elif punya and not hasil[0]:
            self._pesan = "Di folder itu tidak ada foto yang dikenali, jadi lokasinya belum diganti. Pastikan memilih folder yang benar."
        else:
            try:
                library.pindah_sumber(self._c, source_id, akar)
            except ValueError as e:
                self._pesan = f"{e} Lokasinya belum diganti."
            else:
                self._pesan = f"{hasil[0]} dari {punya} foto ditemukan di lokasi baru."
                self._galeri.cekDrive()
                self.sumberBerubah.emit()
                self.pindai(source_id)
        self.berubah.emit()

    @Slot(int)
    def pindai(self, source_id):
        if source_id == self._sumber_aktif or source_id in self._antrean or self._mencari_lokasi:
            return
        self._antrean.append(source_id)
        if self._tahap == "wajah":
            self._batal.set()  # foto baru didahulukan; wajah dilanjutkan sesudahnya
        elif not self._aktif:
            self._mulai_berikut()

    def _mulai_berikut(self):
        self._sumber_aktif = self._antrean.pop(0)
        self._tahap = "foto"
        self._aktif, self._kini, self._total, self._pesan = True, 0, 0, ""
        self._batal.clear()
        self._dijeda_pemakai = False
        self.berubah.emit()
        threading.Thread(target=self._kerja, args=(self._sumber_aktif,), daemon=True).start()

    @Slot()
    def hentikan(self):
        self._antrean.clear()
        self._batal.set()

    @Slot()
    def alihkanJeda(self):
        self._dijeda_pemakai = not self._dijeda_pemakai
        self.berubah.emit()

    @Slot(int)
    def hapus(self, source_id):
        if self._aktif or self._mencari_lokasi:
            return  # pekerja latar masih memakai baris-baris ini
        library.hapus_sumber(self._c, source_id)
        self.sumberBerubah.emit()
        self.perluMuatUlang.emit()

    def _harus_jeda(self):
        b = self._jeda_baterai() and daya.pakai_baterai()
        if b != self._baterai:
            self._baterai = b
            self.berubah.emit()
        dijeda = b or self._dijeda_pemakai
        if dijeda != self._dijeda_terakhir:
            self._dijeda_terakhir = dijeda
            daya.jaga_terjaga(not dijeda)  # hanya menahan laptop tetap hidup selama benar-benar bekerja
        return dijeda

    def _lapor(self, a, b):
        self._maju.emit(a, b)

    def _set_maju(self, a, b):
        self._kini, self._total = a, b
        self.berubah.emit()
        sekarang = time.monotonic()
        if sekarang - self._muat_terakhir >= JEDA_MUAT:
            self._muat_terakhir = sekarang
            self._galeri.muatUlang()

    def _kerja(self, source_id):
        self._dijeda_terakhir = None
        daya.jaga_terjaga(True)
        c = db.buka(self._db)
        try:
            r = scanner.Pemindai(c, self._thumb, self._pekerja).jalankan(
                source_id, batal=self._batal, jeda=self._harus_jeda, lapor=self._lapor)
        except Exception as e:  # jangan biarkan pemindaian mati diam-diam
            r = e
        c.close()
        daya.jaga_terjaga(False)
        self._selesai.emit(r)

    @Slot()
    def lanjutkanWajah(self):
        if not self._model or self._aktif or self._antrean or self._mencari_lokasi or not pipa_wajah.jumlah_belum(self._c):
            return
        self._tahap = "wajah"
        self._kelompok_terakhir = 0
        self._aktif, self._kini, self._total = True, 0, 0  # pesan hasil pindai foto tetap terbaca
        self._batal.clear()
        self._dijeda_pemakai = False
        self.berubah.emit()
        threading.Thread(target=self._kerja_wajah, daemon=True).start()

    def _kerja_wajah(self):
        self._dijeda_terakhir = None
        daya.jaga_terjaga(True)
        c = db.buka(self._db)
        try:
            r = pipa_wajah.PemindaiWajah(c, self._thumb, model=self._model).jalankan(
                batal=self._batal, jeda=self._harus_jeda, lapor=self._lapor_wajah)
        except Exception as e:  # jangan biarkan pekerjaan mati diam-diam
            r = e
        c.close()
        daya.jaga_terjaga(False)
        self._selesai_wajah.emit(r)

    def _lapor_wajah(self, a, b):
        self._maju_wajah.emit(a, b)

    def _set_maju_wajah(self, a, b):
        self._kini, self._total = a, b
        self.berubah.emit()
        if a - self._kelompok_terakhir >= 1000:  # orang mulai terlihat tanpa menunggu berjam-jam
            self._kelompok_terakhir = a
            self.perluKelompok.emit()

    def _usai_wajah(self, r):
        self._aktif, self._tahap, self._dijeda_pemakai = False, "", False
        if isinstance(r, Exception):
            baru = f"Pengenalan wajah berhenti karena ada masalah: {r}"
        elif r.galat_sistem:
            baru = f"Pengenalan wajah berhenti: {r.galat_sistem}"
        elif r.dibatalkan:
            baru = "Pengenalan wajah dihentikan. Bisa dilanjutkan kapan saja dari halaman Lokasi foto."
        else:
            baru = f"Selesai: {r.wajah} wajah ditemukan di {r.selesai} foto."
            if r.menunggu_drive:
                baru += f" {r.menunggu_drive} foto menunggu drive foto dipasang."
            if r.gagal:
                baru += f" {r.gagal} foto tidak bisa diproses."
        self._pesan = " ".join(x for x in (self._pesan, baru) if x)
        self.berubah.emit()
        if not isinstance(r, Exception) and r.selesai:
            self.perluKelompok.emit()
        if self._antrean:
            self._mulai_berikut()

    def _usai(self, r):
        self._aktif, self._sumber_aktif, self._dijeda_pemakai, self._tahap = False, -1, False, ""
        if isinstance(r, Exception):
            self._pesan = f"Pemeriksaan foto berhenti karena ada masalah: {r}"
        elif r.terputus:
            self._pesan = "Drive foto tidak terpasang. Pemeriksaan berhenti dan tidak ada yang hilang."
        elif r.dibatalkan:
            self._pesan = "Pemeriksaan foto dihentikan."
        else:
            bagian = [f"{r.baru} foto baru"]
            if r.dipindah:
                bagian.append(f"{r.dipindah} pindah folder")
            if r.gagal:
                bagian.append(f"{r.gagal} tidak bisa dibuka")
            if r.hilang:
                bagian.append(f"{r.hilang} sudah tidak ada")
            if r.folder_tak_terbaca:
                bagian.append(f"{r.folder_tak_terbaca} folder tidak bisa dibuka")
            self._pesan = "Selesai: " + ", ".join(bagian) + "."
            if r.galat_sistem:
                self._pesan += " Sebagian foto belum tersimpan. Periksa sisa ruang disk, lalu periksa foto baru lagi."
        self.berubah.emit()
        self.sumberBerubah.emit()
        self._galeri.muatUlang()
        if self._antrean:
            self._mulai_berikut()
        elif not (isinstance(r, Exception) or r.dibatalkan):
            self.lanjutkanWajah()
