import threading

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQml import QQmlImageProviderBase
from PySide6.QtQuick import QQuickImageProvider

from core import db, kelompok, orang, thumbs


class PenyediaWajah(QQuickImageProvider):
    """`image://wajah/<sha1>/<x1>,<y1>,<x2>,<y2>`: potongan bulat dari pratinjau, tanpa berkas tambahan."""

    def __init__(self, akar_thumb):
        super().__init__(QQuickImageProvider.ImageType.Image, QQmlImageProviderBase.Flag.ForceAsynchronousImageLoading)
        self._akar = akar_thumb

    def requestImage(self, id_, ukuran, diminta):
        try:
            sha1, kotak = id_.split("/", 1)
            im = thumbs.potong_bulat(self._akar, sha1, [float(v) for v in kotak.split(",")])
            data = im.tobytes("raw", "RGBA")
            return QImage(data, im.width, im.height, QImage.Format.Format_RGBA8888).copy()
        except (OSError, ValueError):  # pratinjau hilang: tampilkan kosong, jangan gagal
            kosong = QImage(1, 1, QImage.Format.Format_RGBA8888)
            kosong.fill(0)
            return kosong


def _url(k):
    return f"image://wajah/{k['sha1']}/{k['x1']:.5f},{k['y1']:.5f},{k['x2']:.5f},{k['y2']:.5f}"


class Orang(QObject):
    berubah = Signal()
    daftarAkanBerubah = Signal()
    daftarBerubah = Signal()
    tinjauBerubah = Signal()
    wajahAkanBerubah = Signal()
    wajahBerubah = Signal()
    _hasil = Signal(object)

    def __init__(self, jalur_db, mulai=False):
        super().__init__()
        self._db = jalur_db
        self._c = db.buka(jalur_db)
        self._daftar = []
        self._jumlah_tinjau = 0
        self._sedang = self._lagi = False
        self._antre, self._i = [], 0
        self._tinjau = {}
        self._wajah_pid = -1
        self._wajah = {}
        self._pesan = ""
        self._pusat = {}
        self._hasil.connect(self._usai)
        self.segarkan()
        if mulai:
            QTimer.singleShot(1500, self._perbarui_bila_perlu)

    # --- daftar
    @Slot()
    def segarkan(self):
        baru = [{"id": d["id"], "nama": d["nama"] or "", "jumlah": d["jumlah"], "url": _url(d["sampul"])}
                for d in orang.daftar(self._c) if d["sampul"]]
        if baru != self._daftar:  # model baru membuat kisi melompat ke atas
            self.daftarAkanBerubah.emit()
            self._daftar = baru
            self.daftarBerubah.emit()
        self._jumlah_tinjau = len(orang.antrean(self._c))
        self.berubah.emit()

    @Property("QVariantList", notify=daftarBerubah)
    def daftar(self):
        return self._daftar

    @Property(int, notify=berubah)
    def jumlahTinjau(self):
        return self._jumlah_tinjau

    @Property(bool, notify=berubah)
    def sedang(self):
        return self._sedang

    @Property(str, notify=berubah)
    def pesan(self):
        return self._pesan

    # --- pengelompokan
    def _perbarui_bila_perlu(self):
        if self._c.execute("SELECT 1 FROM face WHERE state='baru' LIMIT 1").fetchone():
            self.perbarui()

    @Slot()
    def perbarui(self):
        if self._sedang:
            self._lagi = True
            return
        self._sedang = True
        self.berubah.emit()
        threading.Thread(target=self._kerja, daemon=True).start()

    def _kerja(self):
        try:
            r = kelompok.jalankan_di_proses(self._db)
        except Exception as e:  # jangan biarkan pekerjaan mati diam-diam
            r = e
        self._hasil.emit(r)

    def _usai(self, r):
        self._sedang = False
        self._pesan = f"Pengelompokan wajah berhenti karena ada masalah: {r}" if isinstance(r, Exception) else ""
        self.segarkan()
        if self._lagi:
            self._lagi = False
            self.perbarui()

    # --- tinjau
    @Property("QVariantMap", notify=tinjauBerubah)
    def tinjau(self):
        return self._tinjau

    def _muat_tinjau(self):
        while self._i < len(self._antre) and not orang.info(self._c, self._antre[self._i]):
            self._i += 1  # sudah tergabung ke kelompok lain
        if self._i >= len(self._antre):
            self._tinjau = {"selesai": True, "total": len(self._antre)}
        else:
            pid = self._antre[self._i]
            i = orang.info(self._c, pid)
            s = orang.saran(self._c, pid, self._pusat)
            self._tinjau = {
                "selesai": False, "id": pid, "urutan": self._i + 1, "total": len(self._antre), "jumlah": i["jumlah"],
                "wajah": [_url(w) for w in orang.contoh(self._c, pid, 12)],
                "saran": {"id": s["id"], "nama": s["nama"] or "", "url": _url(s["sampul"]), "pita": s["pita"]} if s else None,
            }
        self.tinjauBerubah.emit()

    @Slot()
    def mulaiTinjau(self):
        self._antre, self._i = orang.antrean(self._c), 0
        self._pusat = orang.pusat_semua(self._c)
        self._muat_tinjau()

    @Slot(int)
    def mulaiTinjauDari(self, pid):
        """Beri nama mulai dari orang yang diklik; sisanya tetap urut dari yang fotonya terbanyak."""
        self._antre = [p for p in orang.antrean(self._c) if p != pid]
        self._antre.insert(0, pid)
        self._i = 0
        self._pusat = orang.pusat_semua(self._c)
        self._muat_tinjau()

    @Slot()
    def selesaiTinjau(self):
        self.segarkan()

    def _maju(self):
        self._i += 1  # daftar disegarkan saat keluar: menyegarkan tiap langkah terasa berat di pustaka besar
        self._muat_tinjau()

    @Slot(str)
    def simpanNama(self, nama):
        if " ".join(nama.split()) and self._tinjau.get("id"):
            orang.beri_nama(self._c, self._tinjau["id"], nama)
            self._maju()

    @Slot()
    def lewati(self):
        if not self._tinjau.get("selesai", True):
            self._maju()

    @Slot()
    def gabungSaran(self):
        s = self._tinjau.get("saran")
        if s:
            orang.gabung(self._c, self._tinjau["id"], s["id"])
            self._pusat.pop(self._tinjau["id"], None)
            self._maju()

    @Slot()
    def sembunyikanKini(self):
        if self._tinjau.get("id"):
            orang.sembunyikan(self._c, self._tinjau["id"])
            self._pusat.pop(self._tinjau["id"], None)
            self._maju()

    @Slot(str, result="QVariantList")
    def namaSerupa(self, teks):
        t = teks.strip().casefold()
        if not t:
            return []
        semua = orang.nama_ada(self._c)
        return ([n for n in semua if n.casefold().startswith(t)] + [n for n in semua if t in n.casefold() and not n.casefold().startswith(t)])[:6]

    # --- kelola wajah
    @Property("QVariantMap", notify=wajahBerubah)
    def wajahOrang(self):
        return self._wajah

    def _muat_wajah(self):
        i = orang.info(self._c, self._wajah_pid) if self._wajah_pid >= 0 else None
        self.wajahAkanBerubah.emit()
        self._wajah = {} if not i else {
            "id": i["id"], "nama": i["nama"] or "", "jumlah": i["jumlah"],
            "wajah": [{"id": w["id"], "url": _url(w)} for w in orang.wajah_orang(self._c, i["id"])],
        }
        self.wajahBerubah.emit()

    @Slot(int)
    def bukaWajah(self, pid):
        self._wajah_pid = pid
        self._muat_wajah()

    @Slot(str)
    def gantiNama(self, nama):
        if self._wajah_pid >= 0 and " ".join(nama.split()):
            self._wajah_pid = orang.beri_nama(self._c, self._wajah_pid, nama)
            self._muat_wajah()
            self.segarkan()

    @Slot("QVariantList")
    def bukanDia(self, ids):
        orang.bukan_dia(self._c, [int(i) for i in ids], self._wajah_pid)
        self._muat_wajah()
        self.segarkan()

    @Slot("QVariantList", str)
    def pisahkan(self, ids, nama):
        orang.pisahkan(self._c, [int(i) for i in ids], self._wajah_pid, nama or None)
        self._muat_wajah()
        self.segarkan()
