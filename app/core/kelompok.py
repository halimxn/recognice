"""Mengelompokkan wajah menjadi orang. Hanya menambah: anggota orang tidak pernah diambil oleh algoritme.

Ambang gabung disetel dari pustaka itu sendiri: dua wajah dalam satu foto pasti orang berbeda, jadi
kemiripan pasangan seperti itu menunjukkan seberapa mirip orang-orang di pustaka ini (kerabat, teman
sekelas berseragam). Ukurannya: `dev/eval/tanpa_label.py`. Set emas tetap dibutuhkan untuk angka akurasi.
"""
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np

from core import db, scanner
from core.pipa_wajah import MODEL

AMBANG_TEPI = 0.50       # batas bawah; juga dipakai bila bukti dari pustaka belum cukup
AMBANG_TEPI_MAKS = 0.65  # di atas ini orang yang sama pun mulai terpecah
SELISIH_PUSAT = 0.10     # pusat dua kelompok boleh sedikit kurang mirip daripada tepinya
KUANTIL_BEDA = 99        # kuantil di atasnya berisi kolase, cermin, dan foto di dalam foto
JARAK_AMAN = 0.02
MIN_PASANGAN = 100
MARGIN = 0.06
TAMBAH_KUALITAS_RENDAH = 0.08
MIN_ANGGOTA = 3
K_TETANGGA = 20
K_PROTOTIPE = 5
JARAK_PROTOTIPE = 0.35

MIN_LEBAR, MIN_SKOR, MIN_TAJAM, MIN_FRONTAL = 40, 0.6, 20, 0.35


@dataclass
class RingkasanKelompok:
    wajah: int = 0
    ditugaskan: int = 0
    kelompok_baru: int = 0
    belum: int = 0
    ambang: float = AMBANG_TEPI


def tetangga(V, k, blok=2048):
    """Tetangga terdekat cosine per baris; dipecah per blok agar memori tetap kecil."""
    n = len(V)
    k = min(k, n - 1)
    if k < 1:
        return np.zeros((n, 0), np.int32), np.zeros((n, 0), np.float32)
    idx, skor = np.zeros((n, k), np.int32), np.zeros((n, k), np.float32)
    for a in range(0, n, blok):
        S = V[a:a + blok] @ V.T
        S[np.arange(S.shape[0]), np.arange(a, a + S.shape[0])] = -2
        bagian = np.argpartition(-S, k - 1, axis=1)[:, :k]
        s = np.take_along_axis(S, bagian, 1)
        urut = np.argsort(-s, axis=1)
        idx[a:a + blok] = np.take_along_axis(bagian, urut, 1)
        skor[a:a + blok] = np.take_along_axis(s, urut, 1)
    return idx, skor


def kemiripan_satu_foto(V, foto, pakai):
    """Kemiripan semua pasangan wajah yang berada di foto yang sama: pasangan orang berbeda yang pasti."""
    pilih = np.flatnonzero(pakai)
    if not len(pilih):
        return np.zeros(0, np.float32)
    pilih = pilih[np.argsort(foto[pilih], kind="stable")]
    _, awal = np.unique(foto[pilih], return_index=True)
    hasil = []
    for g in np.split(pilih, awal[1:]):
        if len(g) > 1:
            hasil.append((V[g] @ V[g].T)[np.triu_indices(len(g), 1)])
    return np.concatenate(hasil).astype(np.float32) if hasil else np.zeros(0, np.float32)


def ambang_dari_data(beda):
    """Ambang gabung: sedikit di atas kemiripan yang masih biasa terjadi antara orang berbeda di pustaka ini."""
    beda = beda[np.isfinite(beda)]  # embedding rusak tidak boleh mematikan seluruh pengelompokan
    if len(beda) < MIN_PASANGAN:
        return AMBANG_TEPI
    return float(np.clip(np.percentile(beda, KUANTIL_BEDA) + JARAK_AMAN, AMBANG_TEPI, AMBANG_TEPI_MAKS))


def kelompok_graf(V, foto, beda, ambang=AMBANG_TEPI):
    """Gabung dari sisi terkuat. Sisi harus saling-terdekat; penggabungan ditolak bila
    ada foto yang sama, batasan pemilik, atau kedua pusat kelompok tidak cukup mirip."""
    n = len(V)
    idx, skor = tetangga(V, K_TETANGGA)
    terdekat = [set(idx[i][skor[i] >= ambang].tolist()) for i in range(n)]
    tepi = [(float(s), i, int(j)) for i in range(n) for j, s in zip(idx[i], skor[i])
            if s >= ambang and i < j and i in terdekat[j]]
    tepi.sort(reverse=True)

    induk = list(range(n))
    anggota = [[i] for i in range(n)]
    foto_kel = [{int(f)} for f in foto]
    pusat = V.astype(np.float32).copy()

    def akar(i):
        while induk[i] != i:
            induk[i] = induk[induk[i]]
            i = induk[i]
        return i

    def bentrok(a, b):
        for i in anggota[a]:
            lawan = beda.get(i)
            if lawan and not lawan.isdisjoint(anggota[b]):
                return True
        return False

    for _, i, j in tepi:
        a, b = akar(i), akar(j)
        if a == b:
            continue
        if len(anggota[a]) > len(anggota[b]):
            a, b = b, a
        if not foto_kel[a].isdisjoint(foto_kel[b]) or bentrok(a, b):
            continue
        cos = float(pusat[a] @ pusat[b]) / max(float(np.linalg.norm(pusat[a]) * np.linalg.norm(pusat[b])), 1e-9)
        if cos < ambang - SELISIH_PUSAT:
            continue
        induk[a] = b
        anggota[b] += anggota[a]
        foto_kel[b] |= foto_kel[a]
        pusat[b] += pusat[a]
        anggota[a], foto_kel[a] = [], set()
    return [m for m in anggota if m]


def prototipe(V, kualitas, K=K_PROTOTIPE):
    """Beberapa pusat per orang (kecil-dewasa, berkacamata), dipilih yang saling jauh."""
    if not len(V):
        return np.zeros((0, 512), np.float32)
    bobot = np.maximum(kualitas, 0.01)
    pilih = [int(np.argmax(bobot))]
    while len(pilih) < min(K, len(V)):
        jarak = 1 - (V @ V[pilih].T).max(axis=1)
        j = int(np.argmax(jarak))
        if jarak[j] < JARAK_PROTOTIPE:
            break
        pilih.append(j)
    terdekat = (V @ V[pilih].T).argmax(axis=1)
    hasil = []
    for i in range(len(pilih)):
        m = terdekat == i
        pusat = (V[m] * bobot[m][:, None]).sum(0)
        hasil.append(pusat / max(float(np.linalg.norm(pusat)), 1e-9))
    return np.stack(hasil, dtype=np.float32)


def _tugaskan(calon, orang, V, foto, layak, kualitas, indeks_beda, ambang_tugas):
    """Isi `orang[i]` untuk wajah calon yang jelas mirip satu orang. Kembalikan jumlahnya."""
    terisi = np.flatnonzero(orang != -1)
    if not len(calon) or not len(terisi):
        return 0
    urut = terisi[np.argsort(orang[terisi], kind="stable")]
    id_orang, awal = np.unique(orang[urut], return_index=True)
    potong = np.split(urut, awal[1:])
    protos, batas = [], []
    foto_orang = {}
    for pid, m in zip(id_orang.tolist(), potong):
        foto_orang[pid] = set(foto[m].tolist())
        pakai = m[layak[m]] if layak[m].any() else m
        batas.append(sum(len(p) for p in protos))
        protos.append(prototipe(V[pakai], kualitas[pakai]))
    P = np.vstack(protos)
    batas = np.array(batas)

    tawaran = []
    for a in range(0, len(calon), 2048):
        bag = calon[a:a + 2048]
        M = np.maximum.reduceat(V[bag] @ P.T, batas, axis=1)
        if M.shape[1] == 1:
            s1, top, s2 = M[:, 0], np.zeros(len(bag), int), np.full(len(bag), -1.0)
        else:
            t2 = np.argpartition(-M, 1, axis=1)[:, :2]
            s = np.take_along_axis(M, t2, 1)
            pertama = s.argmax(axis=1)
            baris = np.arange(len(bag))
            s1, top, s2 = s[baris, pertama], t2[baris, pertama], s[baris, 1 - pertama]
        tawaran += zip(s1.tolist(), bag.tolist(), id_orang[top].tolist(), s2.tolist())

    jumlah = 0
    for s1, i, pid, s2 in sorted(tawaran, reverse=True):
        ambang = ambang_tugas + (0 if layak[i] else TAMBAH_KUALITAS_RENDAH)
        if s1 < ambang or s1 - s2 < MARGIN or int(foto[i]) in foto_orang[pid]:
            continue
        if any(orang[g] == pid for g in indeks_beda.get(i, ())):
            continue
        orang[i] = pid
        foto_orang[pid].add(int(foto[i]))
        jumlah += 1
    return jumlah


def kelompokkan(c):
    r = RingkasanKelompok()
    with c:  # foto yang dihapus dari galeri bisa meninggalkan orang tanpa wajah
        c.execute("DELETE FROM person WHERE id NOT IN (SELECT person_id FROM face WHERE person_id IS NOT NULL)")
    baris = c.execute("SELECT id, photo_id, person_id, state, lebar_px, skor, tajam, frontal, kualitas, embedding "
                      "FROM face WHERE model=?", (MODEL,)).fetchall()
    r.wajah = len(baris)
    if not baris:
        return r
    ids = np.array([b[0] for b in baris])
    foto = np.array([b[1] for b in baris])
    orang = np.array([b[2] if b[2] is not None else -1 for b in baris])
    lb, sk, tj, fr, kualitas = (np.array([b[k] for b in baris], np.float32) for k in (4, 5, 6, 7, 8))
    layak = (lb >= MIN_LEBAR) & (sk >= MIN_SKOR) & (tj >= MIN_TAJAM) & (fr >= MIN_FRONTAL)
    V = np.frombuffer(b"".join(b[9] for b in baris), np.float16).reshape(-1, 512).astype(np.float32)
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)

    ke_indeks = {int(f): i for i, f in enumerate(ids)}
    indeks_beda = {}
    for a, b in c.execute("SELECT face_a, face_b FROM batasan WHERE jenis='beda'"):
        if a in ke_indeks and b in ke_indeks:
            ia, ib = ke_indeks[a], ke_indeks[b]
            indeks_beda.setdefault(ia, set()).add(ib)
            indeks_beda.setdefault(ib, set()).add(ia)

    r.ambang = ambang = ambang_dari_data(kemiripan_satu_foto(V, foto, layak))
    r.ditugaskan += _tugaskan(np.flatnonzero(orang == -1), orang, V, foto, layak, kualitas, indeks_beda, ambang)

    kolam = np.flatnonzero((orang == -1) & layak)
    baru = {}  # id sementara (negatif) -> anggota
    if len(kolam) >= MIN_ANGGOTA:
        peta = {int(g): i for i, g in enumerate(kolam)}
        beda_kolam = {peta[i]: {peta[g] for g in s if g in peta} for i, s in indeks_beda.items() if i in peta}
        sementara = -2
        for k in kelompok_graf(V[kolam], foto[kolam], beda_kolam, ambang):
            if len(k) >= MIN_ANGGOTA:
                orang[kolam[k]] = sementara
                baru[sementara] = kolam[k]
                sementara -= 1
    r.kelompok_baru = len(baru)

    r.ditugaskan += _tugaskan(np.flatnonzero(orang == -1), orang, V, foto, layak, kualitas, indeks_beda, ambang)

    # Pemilik bisa mengoreksi selama perhitungan: hanya wajah yang masih kosong yang diisi,
    # dan orang lama ditulis lebih dulu supaya id orang yang baru terhapus tidak terpakai ulang.
    isi = "UPDATE face SET person_id=?, state='otomatis' WHERE id=? AND person_id IS NULL AND EXISTS(SELECT 1 FROM person WHERE id=?)"
    with c:
        c.executemany(isi, [(int(orang[i]), b[0], int(orang[i])) for i, b in enumerate(baris)
                            if b[2] is None and orang[i] >= 0])
        sekarang = int(time.time())
        ganti = {}
        for s, anggota in baru.items():
            ganti[s] = c.execute("INSERT INTO person(dibuat) VALUES (?)", (sekarang,)).lastrowid
        c.executemany(isi, [(ganti[int(orang[i])], baris[i][0], ganti[int(orang[i])]) for i in range(len(baris))
                            if int(orang[i]) in ganti])
        kosong = [(b[0],) for i, b in enumerate(baris) if orang[i] == -1 and b[3] != "belum"]
        r.belum = int((orang == -1).sum())
        c.executemany("UPDATE face SET state='belum' WHERE id=? AND person_id IS NULL", kosong)
    return r


def _jalankan(jalur_db):
    c = db.buka(jalur_db)
    try:
        return kelompokkan(c)
    finally:
        c.close()


def jalankan_di_proses(jalur_db):
    """Proses tersendiri berprioritas rendah: matmul besar tidak boleh mengganggu antarmuka."""
    with ProcessPoolExecutor(1, initializer=scanner._proses_rendah) as p:
        return p.submit(_jalankan, str(jalur_db)).result()
