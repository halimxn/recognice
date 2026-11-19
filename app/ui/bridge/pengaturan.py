import json
import os
import winreg
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot


def _kontras(a, b):
    def lum(h):
        v = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def aksen_dari_palet(p):
    """AccentPalette Windows: 8 warna RGBA dari terang ke gelap.

    Garis dan penanda memakai Light2 di tema gelap; tombol terisi memakai Dark1 seperti Microsoft Photos.
    """
    def warna(i, kanvas, bawaan):
        w = "#" + p[i * 4:i * 4 + 3].hex() if len(p) >= 32 else bawaan
        return w if _kontras(w, kanvas) >= 3 else bawaan  # aksen yang menyatu dengan kanvas tidak terlihat

    hasil = {"gelap": warna(1, "#0a0a0a", "#60cdff"), "isi_gelap": warna(4, "#0a0a0a", "#0067c0"),
             "terang": warna(4, "#f3f3f3", "#005fb8"), "isi_terang": warna(4, "#f3f3f3", "#005fb8")}
    for tema in ("gelap", "terang"):
        hasil["pada_" + tema] = max(("#000000", "#ffffff"), key=lambda t: _kontras(t, hasil["isi_" + tema]))
    return hasil


def baca_palet():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent") as k:
            return winreg.QueryValueEx(k, "AccentPalette")[0]
    except OSError:
        return b""


class Pengaturan(QObject):
    berubah = Signal()

    def __init__(self, jalur):
        super().__init__()
        self._jalur = Path(jalur)
        self._nilai = {"tema": "auto", "tinggiBaris": 170, "jedaBaterai": True, "halamanAwal": "galeri"}
        try:
            self._nilai |= json.loads(self._jalur.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if self._nilai["tema"] not in ("auto", "gelap", "terang"):
            self._nilai["tema"] = "auto"  # tema Krem sudah dihapus

    def _simpan(self):
        self._jalur.parent.mkdir(parents=True, exist_ok=True)
        sementara = self._jalur.with_suffix(".tmp")
        sementara.write_text(json.dumps(self._nilai), encoding="utf-8")
        os.replace(sementara, self._jalur)

    @Property("QVariantMap", constant=True)
    def aksen(self):  # shortcut: dibaca saat mulai, ganti warna Windows berlaku setelah aplikasi dibuka ulang
        return aksen_dari_palet(baca_palet())

    @Property(str, notify=berubah)
    def tema(self):
        return self._nilai["tema"]

    @Slot(str)
    def aturTema(self, t):
        self._nilai["tema"] = t
        self._simpan()
        self.berubah.emit()

    @Property(str, notify=berubah)
    def halamanAwal(self):
        return self._nilai["halamanAwal"]

    @Slot(str)
    def aturHalamanAwal(self, h):
        self._nilai["halamanAwal"] = h
        self._simpan()
        self.berubah.emit()

    @Property(int, notify=berubah)
    def tinggiBaris(self):
        return self._nilai["tinggiBaris"]

    @Slot(int)
    def aturTinggiBaris(self, t):
        self._nilai["tinggiBaris"] = t
        self._simpan()
        self.berubah.emit()

    @Property(bool, notify=berubah)
    def jedaBaterai(self):
        return self._nilai["jedaBaterai"]

    @Slot(bool)
    def aturJedaBaterai(self, v):
        self._nilai["jedaBaterai"] = v
        self._simpan()
        self.berubah.emit()
