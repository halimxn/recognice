"""Tahap B: deteksi di pratinjau SSD, haluskan titik tiap wajah, potong wajah kecil dari foto asli, embedding, simpan."""
import math
import os
import time
from collections import deque
from concurrent.futures import BrokenExecutor, ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from core import faces, library, scanner, thumbs

# Tanda ini ikut berganti bila cara memotong wajah berubah: embedding lama tidak sebanding dengan yang baru.
MODEL = "det10g-640-halus192+w600k_r50"
SISI_DETEKSI = 640
SISI_HALUS = 192
LEBAR_POTONGAN = 2.2  # potongan untuk deteksi ulang, dalam kelipatan lebar wajah
AMBANG_HALUS = 0.4
MIN_PRATINJAU = 112  # di bawah ini pratinjau terlalu kasar untuk embedding
ANTRE = 3
BATAS_BERUNTUN = 5  # kegagalan berturut-turut berarti masalahnya di model atau mesin, bukan fotonya


class PerluAsli(Exception):
    """Wajah kecil butuh foto asli dan drive tidak tersedia; dicoba lagi nanti."""


class GagalWajah(Exception):
    """Foto ini tidak bisa diproses; dicatat dan tidak diulang untuk model yang sama."""


def nilai_kualitas(potongan, skor, lebar_px, titik):
    """Nilai mentah, ambangnya belum dikalibrasi: keputusan layak-tidaknya di tahap pengelompokan."""
    abu = np.asarray(potongan.convert("L"), np.float32)
    lap = abu[:-2, 1:-1] + abu[2:, 1:-1] + abu[1:-1, :-2] + abu[1:-1, 2:] - 4 * abu[1:-1, 1:-1]
    tajam = float(lap.var())
    t = np.asarray(titik, np.float32)
    kiri, kanan = float(np.linalg.norm(t[2] - t[0])), float(np.linalg.norm(t[2] - t[1]))
    frontal = 1 - min(1.0, 2 * abs(kiri - kanan) / max(kiri + kanan, 1e-6))
    kualitas = skor * math.sqrt(min(1.0, lebar_px / 112)) * math.sqrt(min(1.0, tajam / 500)) * frontal
    return {"tajam": tajam, "frontal": frontal, "kualitas": kualitas}


def haluskan(sumber, kotak, det):
    """Lima titik wajah dari deteksi ulang pada potongan di sekitar `kotak`; None bila wajahnya tidak ketemu lagi.

    Deteksi pertama berjalan di kanvas 640, jadi wajah kecil hanya belasan piksel dan titiknya kasar.
    Titik yang meleset membuat potongan miring, dan orang berbeda jadi tampak mirip (dev/bench/HASIL.md).
    """
    x1, y1, x2, y2 = (float(v) for v in kotak)
    lebar = x2 - x1
    s = LEBAR_POTONGAN * max(lebar, y2 - y1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    kiri, atas = int(max(0, cx - s / 2)), int(max(0, cy - s / 2))
    kanan, bawah = int(min(sumber.width, cx + s / 2)), int(min(sumber.height, cy + s / 2))
    if kanan - kiri < 8 or bawah - atas < 8:
        return None
    pusat = np.array([cx - kiri, cy - atas])
    calon = det.deteksi(sumber.crop((kiri, atas, kanan, bawah)), sisi=SISI_HALUS, ambang=AMBANG_HALUS)
    if not calon:
        return None

    def jarak(w):
        return float(np.linalg.norm((w.kotak[:2] + w.kotak[2:]) / 2 - pusat))

    terdekat = min(calon, key=jarak)  # di kerumunan rapat, skor tertinggi bisa milik wajah tetangga
    return terdekat.titik + [kiri, atas] if jarak(terdekat) <= 0.5 * lebar else None


def proses_foto(pratinjau, ambil_asli, det, rec):
    """Kembalikan baris (x1,y1,x2,y2,titik,skor,lebar_px,tajam,frontal,kualitas,embedding); koordinat relatif."""
    wajah = det.deteksi(pratinjau, sisi=SISI_DETEKSI)
    if not wajah:
        return []
    lp, tp = pratinjau.size
    lebar = [float(w.kotak[2] - w.kotak[0]) for w in wajah]
    asli, skala = None, 1.0
    if max(pratinjau.size) >= thumbs.BESAR and min(lebar) < MIN_PRATINJAU:
        asli = ambil_asli(math.ceil(max(pratinjau.size) * MIN_PRATINJAU / max(min(lebar), 1)))
        if asli is None:
            raise PerluAsli()
        skala = asli.width / lp
        if abs(asli.height / tp - skala) > 0.02 * skala:
            raise PerluAsli()  # foto berubah sejak pratinjau dibuat; tunggu pindai berikutnya

    potongan, nilai = [], []
    for w, l in zip(wajah, lebar):
        sumber, k = (asli, skala) if asli is not None and l < MIN_PRATINJAU else (pratinjau, 1.0)
        halus = haluskan(sumber, w.kotak * k, det)
        if halus is not None:
            w.titik = halus / k
        p = faces.sejajarkan(sumber, w.titik * k)
        potongan.append(p)
        nilai.append((l * k, nilai_kualitas(p, w.skor, l * k, w.titik)))

    vektor = rec.embed(potongan).astype(np.float16)
    hasil = []
    for w, (lebar_px, n), v in zip(wajah, nilai, vektor):
        x1, y1, x2, y2 = (float(a) for a in w.kotak)
        titik = (w.titik / [lp, tp]).astype(np.float32).tobytes()
        hasil.append((max(x1 / lp, 0.0), max(y1 / tp, 0.0), min(x2 / lp, 1.0), min(y2 / tp, 1.0), titik, w.skor,
                      lebar_px, n["tajam"], n["frontal"], n["kualitas"], v.tobytes()))
    return hasil


# --- proses pekerja
_det = _rec = None


def muat(jalur_det, jalur_rec, benang, cache=None, alat=None):
    """`alat` None = pilih sendiri (kartu grafis Intel bila ada). `cache` = folder hasil kompilasi OpenVINO."""
    global _det, _rec
    scanner._proses_rendah()
    scanner.siapkan_pillow()
    alat = alat or faces.pilih_alat()
    _det = faces.Detektor(jalur_det, benang, alat, cache)
    _rec = faces.Pengenal(jalur_rec, benang, alat, cache)


def siap():
    """Nama mesin hitung yang benar-benar dipakai, mis. 'openvino-GPU' atau 'ort'."""
    return faces.nama_mesin(_rec.sesi) if _rec else "ort"


def _pengambil(jalur, ukuran, mtime_ns):
    def ambil(sisi):
        if jalur is None:
            return None
        p = scanner._panjang(jalur)
        try:
            st = os.stat(p)
            if (st.st_size, st.st_mtime_ns) != (ukuran, mtime_ns):
                return None  # berubah sejak dipindai: titik wajah tidak lagi cocok
            im = Image.open(p)
            im.draft("RGB", (sisi, sisi))
            return ImageOps.exif_transpose(im).convert("RGB")
        except OSError as e:
            if e.errno is not None:
                return None  # drive terlepas atau file terkunci; dicoba lagi nanti
            raise  # tanpa errno: isi file memang rusak

    return ambil


def olah_foto(tugas):
    pratinjau, asli, ukuran, mtime_ns = tugas
    try:
        with Image.open(pratinjau) as im:
            gambar = im.convert("RGB")
        return proses_foto(gambar, _pengambil(asli, ukuran, mtime_ns), _det, _rec)
    except (PerluAsli, MemoryError):
        raise
    except OSError as e:
        if e.errno is not None:
            raise  # lingkungan (pratinjau hilang dan sejenisnya): foto tidak salah
        raise GagalWajah(repr(e)[:300]) from None
    except Exception as e:
        raise GagalWajah(repr(e)[:300]) from None


@dataclass
class RingkasanWajah:
    total: int = 0
    selesai: int = 0
    wajah: int = 0
    gagal: int = 0
    menunggu_drive: int = 0
    galat_sistem: str = ""
    dibatalkan: bool = False


def jumlah_belum(c):
    return c.execute("SELECT count(*) FROM photo WHERE status='ok' AND sha1 IS NOT NULL "
                     "AND (wajah_model IS NULL OR wajah_model != ?)", (MODEL,)).fetchone()[0]


class PemindaiWajah:
    def __init__(self, c, akar_thumb, model=None, olah=olah_foto, muat=muat):
        """`model` = (jalur detektor, jalur pengenal, benang)."""
        self.c, self.akar_thumb, self.olah, self.muat = c, akar_thumb, olah, muat
        self.args = model or ()

    def _pool(self):
        return ProcessPoolExecutor(1, initializer=self.muat, initargs=self.args)

    def _tugas(self, baris, akar):
        _, sid, rel, sha1, ukuran, mtime_ns = baris
        dasar = akar.get(sid)
        return (str(thumbs.jalur(self.akar_thumb, sha1, thumbs.BESAR)),
                os.path.join(dasar, rel.replace("/", "\\")) if dasar else None, ukuran, mtime_ns)

    def _sendiri(self, tugas):
        """Ulangi di proses baru: pekerja bisa mati karena hal lain, bukan karena foto ini."""
        p = self._pool()
        try:
            return p.submit(self.olah, tugas).result()
        except BrokenExecutor:
            raise GagalWajah("proses pengenal berhenti pada foto ini") from None
        finally:
            p.shutdown(wait=True, cancel_futures=True)

    def _simpan(self, photo_id, hasil):
        c = self.c
        c.execute("DELETE FROM face WHERE photo_id=?", (photo_id,))
        c.executemany("INSERT INTO face(photo_id, x1, y1, x2, y2, titik, skor, lebar_px, tajam, frontal, kualitas, "
                      "embedding, model) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      [(photo_id, *h, MODEL) for h in hasil])
        c.execute("UPDATE photo SET wajah_model=?, wajah_galat=NULL WHERE id=?", (MODEL, photo_id))

    def _catat_gagal(self, photo_id, pesan):
        self.c.execute("DELETE FROM face WHERE photo_id=?", (photo_id,))
        self.c.execute("UPDATE photo SET wajah_model=?, wajah_galat=? WHERE id=?", (MODEL, pesan, photo_id))

    def jalankan(self, batal=None, jeda=None, lapor=None, batas=None):
        r = RingkasanWajah()
        c = self.c
        kerja = c.execute("SELECT id, source_id, rel, sha1, ukuran, mtime_ns FROM photo WHERE status='ok' AND sha1 IS NOT NULL "
                          "AND (wajah_model IS NULL OR wajah_model != ?) ORDER BY taken_at DESC, id DESC",
                          (MODEL,)).fetchall()
        if batas is not None:
            kerja = kerja[:batas]
        r.total = len(kerja)
        if not kerja:
            return r
        akar = {sid: library.akar_sumber(c, sid) for sid in {b[1] for b in kerja}}

        def pool_baru():
            p = self._pool()
            p.submit(siap).result()  # model rusak harus ketahuan di sini, bukan menandai semua foto gagal
            return p

        try:
            pool = pool_baru()
        except BrokenExecutor:
            r.galat_sistem = "Pengenal wajah tidak bisa dijalankan."
            return r

        antre = deque()
        curiga = []  # kegagalan baru dipercaya bila foto lain berhasil sesudahnya
        putus = False
        olahan = 0
        komit = time.monotonic()

        def lepaskan_curiga():
            for photo_id, pesan in curiga:
                self._catat_gagal(photo_id, pesan)
                r.gagal += 1
            curiga.clear()

        def tangani(baris, ambil):
            nonlocal olahan, komit, putus
            try:
                hasil = ambil()
            except BrokenExecutor:
                raise
            except PerluAsli:
                r.menunggu_drive += 1
            except GagalWajah as e:
                curiga.append((baris[0], str(e)))
                if len(curiga) >= BATAS_BERUNTUN:
                    putus = True
                    r.galat_sistem = f"{BATAS_BERUNTUN} foto berturut-turut gagal; kemungkinan berkas pengenal wajah rusak."
            except Exception as e:  # kehabisan memori, pratinjau hilang: foto tidak salah, dicoba lagi nanti
                r.gagal += 1
                r.galat_sistem = repr(e)[:300]
            else:
                lepaskan_curiga()
                self._simpan(baris[0], hasil)
                r.selesai += 1
                r.wajah += len(hasil)
            olahan += 1
            if time.monotonic() - komit >= 1:
                c.commit()
                komit = time.monotonic()
            if lapor and olahan % 10 == 0:
                lapor(olahan, r.total)

        def selesaikan_satu():
            nonlocal pool
            baris, masa = antre[0]
            try:
                tangani(baris, masa.result)
            except BrokenExecutor:
                # Hanya satu pekerja: yang terdepanlah yang sedang dikerjakan saat ia mati
                antre.popleft()
                sisa = [b for b, _ in antre]
                antre.clear()
                pool.shutdown(wait=False, cancel_futures=True)
                tangani(baris, lambda: self._sendiri(self._tugas(baris, akar)))
                pool = pool_baru()
                for b in sisa:
                    antre.append((b, pool.submit(self.olah, self._tugas(b, akar))))
            else:
                antre.popleft()

        try:
            for baris in kerja:
                if putus:
                    break
                if jeda and jeda():
                    c.commit()
                    while jeda() and not (batal and batal.is_set()):
                        time.sleep(0.2)
                if batal and batal.is_set():
                    r.dibatalkan = True
                    break
                if len(antre) >= ANTRE:
                    selesaikan_satu()
                while True:
                    try:
                        antre.append((baris, pool.submit(self.olah, self._tugas(baris, akar))))
                        break
                    except BrokenExecutor:
                        if not antre:
                            raise
                        selesaikan_satu()
            while antre and not putus:
                selesaikan_satu()
            if not (putus or r.dibatalkan):
                lepaskan_curiga()
        except BrokenExecutor:
            r.galat_sistem = "Pengenal wajah tidak bisa dijalankan."
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
            c.commit()
        if lapor:
            lapor(olahan, r.total)
        return r
