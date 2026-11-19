import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import cari, db, pipa_wajah, scanner
from ui.bridge.orang import _url


class Cari(QObject):
    hasilBerubah = Signal()
    saranBerubah = Signal()
    _selesai = Signal(int, object)

    def __init__(self, jalur_db, akar_thumb, model=None, olah=cari.olah_contoh, muat=pipa_wajah.muat):
        super().__init__()
        self._db, self._thumb, self._model, self._olah, self._muat = jalur_db, akar_thumb, model, olah, muat
        self._c = db.buka(jalur_db)
        self._hasil = {"status": "kosong"}
        self._saran = {"orang": [], "folder": [], "tanggal": []}
        self._token = 0
        self._vektor = []
        self._kunci = threading.Lock()
        self._kunci_folder, self._folder = None, None
        self._indeks = None
        self._selesai.connect(self._terima)

    @Property("QVariantMap", notify=hasilBerubah)
    def hasil(self):
        return self._hasil

    @Property(bool, notify=hasilBerubah)
    def bisaContoh(self):
        return self._model is not None

    @Property("QVariantMap", notify=saranBerubah)
    def saran(self):
        return self._saran

    # --- teks
    @Slot(str)
    def ketik(self, teks):
        kunci = self._c.execute("SELECT count(*), max(id) FROM photo WHERE status='ok'").fetchone()
        if kunci != self._kunci_folder:
            self._kunci_folder, self._folder = kunci, cari.hitung_folder(self._c)
        s = cari.saran_teks(self._c, teks, self._folder)
        s["orang"] = [{"id": o["id"], "nama": o["nama"], "jumlah": o["jumlah"], "url": _url(o["sampul"])} for o in s["orang"] if o["sampul"]]
        self._saran = s
        self.saranBerubah.emit()

    @Slot()
    def bersihkan(self):
        self._saran = {"orang": [], "folder": [], "tanggal": []}
        self.saranBerubah.emit()

    @Slot(result="QVariantMap")
    def saringanHasil(self):
        return {"foto": [w["photoId"] for w in self._hasil.get("wajah", [])], "label": "Hasil pencarian wajah"}

    # --- wajah
    def _mulai(self, kerja):
        self._token += 1
        self._hasil = {"status": "memproses"}
        self.hasilBerubah.emit()
        threading.Thread(target=kerja, args=(self._token,), daemon=True).start()

    def _kirim(self, token, data):
        self._selesai.emit(token, data)

    def _terima(self, token, data):
        if token == self._token:  # jawaban permintaan lama diabaikan
            if "vektor" in data:
                self._vektor = data.pop("vektor")
            self._hasil = data
            self.hasilBerubah.emit()

    def _pesan(self, teks):
        self._token += 1
        self._hasil = {"status": "pesan", "pesan": teks}
        self.hasilBerubah.emit()

    @Slot(str)
    def contohUrl(self, url):
        self.contoh(os.path.normpath(QUrl(url).toLocalFile()))

    @Slot(str)
    def contoh(self, jalur):
        if os.path.splitext(jalur)[1].lower() not in scanner.EXT_FOTO:
            self._pesan("Jenis berkas ini tidak bisa dipakai. Pakai foto JPEG, PNG, WebP, atau HEIC.")
        elif self._model is None:
            self._pesan("Berkas pengenal wajah tidak ada.")
        else:
            self._mulai(lambda token: self._kerja_contoh(token, jalur))

    def _kerja_contoh(self, token, jalur):
        try:
            with ProcessPoolExecutor(1, initializer=self._muat, initargs=self._model) as p:
                sha1, wajah = p.submit(self._olah, jalur, str(self._thumb)).result()
        except Exception:  # file rusak, terkunci, atau pekerja mati: pemilik cukup tahu tidak terbaca
            self._kirim(token, {"status": "pesan", "pesan": "Foto ini tidak bisa dibaca."})
            return
        if not wajah:
            self._kirim(token, {"status": "pesan", "pesan": "Tidak ada wajah yang terlihat di foto ini."})
            return
        vektor = [np.frombuffer(w[4], np.float16).astype(np.float32) for w in wajah]
        pilihan = [{"i": i, "url": _url({"sha1": sha1, "x1": w[0], "y1": w[1], "x2": w[2], "y2": w[3]})} for i, w in enumerate(wajah)]
        if len(wajah) > 1:
            self._kirim(token, {"status": "pilih", "pilihan": pilihan, "vektor": vektor})
        else:
            self._cari(token, vektor[0], pilihan[0]["url"])

    @Slot(int)
    def pilihWajah(self, i):
        pilihan = self._hasil.get("pilihan", [])
        if not 0 <= i < min(len(pilihan), len(self._vektor)):
            return
        url = pilihan[i]["url"]
        v = self._vektor[i]
        self._mulai(lambda token: self._cari(token, v, url))

    @Slot(int)
    def dariWajah(self, face_id):
        self._mulai(lambda token: self._cari(token, None, "", face_id))

    def _cari(self, token, v, url_kueri, face_id=None):
        c = db.buka(self._db)
        try:
            with self._kunci:
                if self._indeks is None:
                    self._indeks = cari.Indeks(c)
                self._indeks.c = c
                if face_id is not None:
                    b = c.execute("SELECT ph.sha1, f.x1, f.y1, f.x2, f.y2 FROM face f JOIN photo ph ON ph.id=f.photo_id WHERE f.id=?",
                                  (face_id,)).fetchone()
                    url_kueri = _url(dict(zip(("sha1", "x1", "y1", "x2", "y2"), b)))
                    v = self._indeks.vektor(face_id)
                t = time.perf_counter()
                h = self._indeks.cari(v, kecuali=face_id)
                ms = (time.perf_counter() - t) * 1000
            self._kirim(token, {
                "status": "hasil", "kueri": url_kueri, "ms": round(ms),
                "orang": [{"id": o["id"], "nama": o["nama"] or "", "jumlah": o["jumlah"], "pita": o["pita"], "url": _url(o["sampul"])} for o in h["orang"]],
                "wajah": [{"id": w["id"], "photoId": w["photo_id"], "pita": w["pita"], "url": _url(w)} for w in h["wajah"]],
            })
        except KeyError:  # wajah dari model lama belum punya embedding yang bisa dibandingkan
            self._kirim(token, {"status": "pesan", "pesan": "Wajah ini belum selesai dikenali. Coba lagi nanti."})
        except Exception as e:  # jangan biarkan layar menunggu selamanya
            self._kirim(token, {"status": "pesan", "pesan": f"Pencarian berhenti karena ada masalah: {e}"})
        finally:
            c.close()
