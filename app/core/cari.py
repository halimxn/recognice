"""Pencarian: saran dari teks, dan wajah serupa lewat matmul pada seluruh embedding."""
import calendar
import hashlib
import io
import re
from collections import Counter

import numpy as np
from PIL import Image, ImageOps

from core import library, orang, pipa_wajah, scanner, thumbs
from core.pipa_wajah import MODEL

AMBANG = 0.40  # belum dikalibrasi; batas pita "Mungkin"
BATAS_HIT = 2000
BULAN = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober",
         "november", "desember"]


def hitung_folder(c):
    """Jumlah foto per folder, termasuk subfolder. Terpisah agar tidak dihitung ulang tiap ketukan."""
    hasil = Counter()
    for sid, rel in c.execute("SELECT source_id, rel FROM photo WHERE status='ok'"):
        bagian = rel.split("/")[:-1]
        for n in range(1, len(bagian) + 1):
            hasil[sid, "/".join(bagian[:n])] += 1
    return hasil


def saran_teks(c, teks, folder_terhitung=None):
    t = " ".join(teks.split()).casefold()
    if not t:
        return {"orang": [], "folder": [], "tanggal": []}

    nama = [b for b in c.execute("SELECT id, nama FROM person WHERE nama IS NOT NULL AND tersembunyi=0") if t in b[1].casefold()]
    nama.sort(key=lambda b: (not b[1].casefold().startswith(t), b[1].casefold()))
    daftar_orang = [i for i in (orang.info(c, b[0]) for b in nama[:5]) if i]

    hitung = hitung_folder(c) if folder_terhitung is None else folder_terhitung
    folder = [{"source": s, "rel": r, "jumlah": j} for (s, r), j in hitung.items() if t in r.casefold()]
    folder.sort(key=lambda f: (-f["jumlah"], f["rel"]))

    return {"orang": daftar_orang, "folder": folder[:5], "tanggal": _tanggal(c, t)}


def _tanggal(c, t):
    m = re.fullmatch(r"(?:([a-z]{3,}) )?(\d{4})", t)
    if not m:
        return []
    tahun, kata = int(m[2]), m[1]
    bulan = 0
    if kata:
        cocok = [i for i, b in enumerate(BULAN, 1) if b.startswith(kata)]
        if len(cocok) != 1:
            return []
        bulan = cocok[0]
    if not 1970 <= tahun <= 3000:
        return []
    jumlah = library.hitung(c, {"tahun": tahun, "bulan": bulan})
    if not jumlah:
        return []
    label = f"{BULAN[bulan - 1].capitalize()} {tahun}" if bulan else str(tahun)
    return [{"label": label, "tahun": tahun, "bulan": bulan, "jumlah": jumlah}]


class Indeks:
    """Matriks embedding di memori. Disegarkan bila jumlah wajah berubah."""

    def __init__(self, c):
        self.c = c
        self._kunci = None
        self._ids = np.zeros(0, np.int64)
        self._V = np.zeros((0, 512), np.float32)

    def _muat_matriks(self, ids, V):
        self._ids, self._V = ids, V

    def _segarkan(self):
        kunci = self.c.execute("SELECT count(*), max(id), total(kualitas) FROM face WHERE model=?", (MODEL,)).fetchone()
        if kunci == self._kunci:
            return
        baris = self.c.execute("SELECT id, embedding FROM face WHERE model=? ORDER BY id", (MODEL,)).fetchall()
        self._kunci = kunci
        if not baris:
            self._muat_matriks(np.zeros(0, np.int64), np.zeros((0, 512), np.float32))
            return
        V = np.frombuffer(b"".join(b[1] for b in baris), np.float16).reshape(-1, 512).astype(np.float32)
        V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
        self._muat_matriks(np.array([b[0] for b in baris], np.int64), V)

    def vektor(self, face_id):
        self._segarkan()
        i = int(np.searchsorted(self._ids, face_id))
        if i >= len(self._ids) or self._ids[i] != face_id:
            raise KeyError(face_id)
        return self._V[i].copy()

    def _peringkat(self, q, kecuali):
        if not len(self._ids):
            return [], []
        s = self._V @ q
        pilih = np.flatnonzero(s >= AMBANG)
        pilih = pilih[np.argsort(-s[pilih], kind="stable")[:BATAS_HIT + 1]]
        ids = self._ids[pilih].tolist()
        skor = s[pilih].tolist()
        if kecuali is not None and kecuali in ids:
            k = ids.index(kecuali)
            del ids[k], skor[k]
        return ids[:BATAS_HIT], skor[:BATAS_HIT]

    def cari(self, v, kecuali=None, batas=300):
        q = np.asarray(v, np.float32)
        q /= max(float(np.linalg.norm(q)), 1e-9)
        self._segarkan()
        ids, skor = self._peringkat(q, kecuali)
        if not ids:
            return {"orang": [], "wajah": []}
        c = self.c
        tanda = ",".join("?" * len(ids))
        rinci = {b[0]: b[1:] for b in c.execute(
            f"SELECT f.id, f.person_id, ph.id, ph.sha1, f.x1, f.y1, f.x2, f.y2 FROM face f "
            f"JOIN photo ph ON ph.id=f.photo_id AND ph.status='ok' LEFT JOIN person p ON p.id=f.person_id "
            f"WHERE f.id IN ({tanda}) AND COALESCE(p.tersembunyi, 0)=0", ids)}

        wajah, per_orang = [], {}
        for fid, s in zip(ids, skor):
            r = rinci.get(fid)
            if r is None:
                continue
            if r[0] is not None:
                per_orang.setdefault(r[0], []).append(s)
            if len(wajah) < batas:
                wajah.append({"id": fid, "photo_id": r[1], "sha1": r[2], "x1": r[3], "y1": r[4], "x2": r[5], "y2": r[6],
                              "pita": orang._pita(s)})

        hasil_orang = []
        for pid, nilai in per_orang.items():
            total = c.execute("SELECT count(*) FROM face WHERE person_id=?", (pid,)).fetchone()[0]
            # Rata-rata 3 teratas: satu wajah keliru di kelompok besar tidak mengangkat orang itu
            skor_orang = sum(sorted(nilai, reverse=True)[:3]) / min(3, max(total, 1))
            if skor_orang >= AMBANG:
                hasil_orang.append((skor_orang, pid))
        hasil_orang.sort(reverse=True)
        keluar = []
        for s, pid in hasil_orang[:8]:
            i = orang.info(c, pid)
            if i and i["sampul"]:
                keluar.append({**i, "pita": orang._pita(s)})
        return {"orang": keluar, "wajah": wajah}


def olah_contoh(jalur, akar_thumb):
    """Dijalankan di proses yang sudah `pipa_wajah.muat`. Foto contoh hanya dibaca."""
    with open(scanner._panjang(jalur), "rb") as f:
        data = f.read()
    sha1 = hashlib.sha1(data).hexdigest()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    thumbs.buat(im, akar_thumb, sha1)
    with Image.open(thumbs.jalur(akar_thumb, sha1, thumbs.BESAR)) as p:
        pratinjau = p.convert("RGB")
    hasil = pipa_wajah.proses_foto(pratinjau, lambda _: im, pipa_wajah._det, pipa_wajah._rec)
    return sha1, [(h[0], h[1], h[2], h[3], h[10]) for h in hasil]
