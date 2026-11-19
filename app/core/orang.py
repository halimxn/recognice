"""Tindakan pemilik atas orang. Koreksi ditulis sebagai batasan wajah, jadi bertahan saat dikelompokkan ulang."""
import time

import numpy as np

from core.kelompok import MIN_ANGGOTA

_HITUNG = ("FROM person p JOIN face f ON f.person_id=p.id JOIN photo ph ON ph.id=f.photo_id AND ph.status='ok' "
           "WHERE p.tersembunyi=0 GROUP BY p.id ")


JANGKAR_TOLAK = 50  # penolakan bertahan walau sebagian wajah orang itu kelak dikeluarkan juga


def _kotak(sha1, x1, y1, x2, y2):
    return {"sha1": sha1, "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _sampul(c, pid):
    b = c.execute("SELECT ph.sha1, f.x1, f.y1, f.x2, f.y2 FROM face f JOIN photo ph ON ph.id=f.photo_id "
                  "WHERE f.person_id=? AND ph.status='ok' ORDER BY f.kualitas DESC LIMIT 1", (pid,)).fetchone()
    return _kotak(*b) if b else None


def _info(c, pid, nama, jumlah):
    return {"id": pid, "nama": nama, "jumlah": jumlah, "sampul": _sampul(c, pid)}


def daftar(c):
    """Orang bernama selalu tampil; kelompok tanpa nama hanya bila cukup foto."""
    baris = c.execute("SELECT p.id, p.nama, count(DISTINCT f.photo_id) j " + _HITUNG +
                      "HAVING j >= ? OR p.nama IS NOT NULL OR EXISTS(SELECT 1 FROM face y WHERE y.person_id=p.id AND y.state='yakin') "
                      "ORDER BY j DESC, p.id", (MIN_ANGGOTA,)).fetchall()
    return [_info(c, *b) for b in baris]


def info(c, pid):
    b = c.execute("SELECT p.id, p.nama, count(DISTINCT f.photo_id) FROM person p JOIN face f ON f.person_id=p.id "
                  "JOIN photo ph ON ph.id=f.photo_id AND ph.status='ok' WHERE p.id=? GROUP BY p.id", (pid,)).fetchone()
    return _info(c, *b) if b else None


def antrean(c):
    return [b[0] for b in c.execute(
        "SELECT p.id, count(DISTINCT f.photo_id) j " + _HITUNG + "HAVING p.nama IS NULL AND j >= ? ORDER BY j DESC, p.id",
        (MIN_ANGGOTA,))]


def nama_ada(c):
    return [b[0] for b in c.execute("SELECT nama FROM person p WHERE nama IS NOT NULL AND tersembunyi=0 "
                                    "AND EXISTS(SELECT 1 FROM face f WHERE f.person_id=p.id) ORDER BY nama")]


def _pasang(c, a, b, jenis):
    if a != b:
        c.execute("INSERT OR REPLACE INTO batasan(face_a, face_b, jenis) VALUES (?,?,?)", (min(a, b), max(a, b), jenis))


def _jangkar(c, pid, kecuali=(), n=5):
    kecuali = set(kecuali)
    hasil = [b[0] for b in c.execute("SELECT id FROM face WHERE person_id=? ORDER BY kualitas DESC, id LIMIT ?",
                                     (pid, n + len(kecuali)))]
    return [f for f in hasil if f not in kecuali][:n]


def _bersihkan(c, pid):
    if not c.execute("SELECT 1 FROM face WHERE person_id=? LIMIT 1", (pid,)).fetchone():
        c.execute("DELETE FROM person WHERE id=?", (pid,))


def beri_nama(c, pid, nama):
    """Nama yang sudah dipakai berarti orang yang sama: kelompoknya digabung. Kembalikan id orang."""
    nama = " ".join(nama.split())
    if not nama:
        raise ValueError("nama kosong")
    for lain, n in c.execute("SELECT id, nama FROM person WHERE nama IS NOT NULL AND id != ?", (pid,)).fetchall():
        if n.casefold() == nama.casefold():
            gabung(c, pid, lain)
            return lain
    with c:
        c.execute("UPDATE person SET nama=? WHERE id=?", (nama, pid))
    return pid


def gabung(c, sumber, tujuan):
    if sumber == tujuan:
        return
    with c:
        a, b = _jangkar(c, sumber, n=1), _jangkar(c, tujuan, n=1)
        if a and b:
            _pasang(c, a[0], b[0], "sama")
        nama = c.execute("SELECT nama FROM person WHERE id=?", (sumber,)).fetchone()[0]
        c.execute("UPDATE person SET nama=COALESCE(nama, ?) WHERE id=?", (nama, tujuan))
        c.execute("UPDATE face SET person_id=? WHERE person_id=?", (tujuan, sumber))
        c.execute("DELETE FROM person WHERE id=?", (sumber,))


def bukan_dia(c, face_ids, pid):
    with c:
        jangkar = _jangkar(c, pid, kecuali=face_ids, n=JANGKAR_TOLAK)
        for f in face_ids:
            for a in jangkar:
                _pasang(c, f, a, "beda")
            c.execute("UPDATE face SET person_id=NULL, state='belum' WHERE id=? AND person_id=?", (f, pid))
        _bersihkan(c, pid)


def tetapkan(c, face_ids, pid):
    """Wajah ini memang orang ini. Yang terbaru menang atas batasan lama."""
    with c:
        jangkar = _jangkar(c, pid, kecuali=face_ids)
        for f in face_ids:
            c.execute("DELETE FROM batasan WHERE jenis='beda' AND ((face_a=? AND face_b IN (SELECT id FROM face WHERE person_id=?)) "
                      "OR (face_b=? AND face_a IN (SELECT id FROM face WHERE person_id=?)))", (f, pid, f, pid))
            for a in jangkar:
                _pasang(c, f, a, "sama")
            c.execute("UPDATE face SET person_id=?, state='yakin' WHERE id=?", (pid, f))


def pisahkan(c, face_ids, pid, nama=None):
    with c:
        jangkar = _jangkar(c, pid, kecuali=face_ids, n=JANGKAR_TOLAK)
        lama = c.execute("SELECT nama FROM person WHERE id=?", (pid,)).fetchone()[0]
        baru = c.execute("INSERT INTO person(dibuat) VALUES (?)", (int(time.time()),)).lastrowid
        for f in face_ids:
            for a in jangkar:
                _pasang(c, f, a, "beda")
            c.execute("UPDATE face SET person_id=?, state='yakin' WHERE id=? AND person_id=?", (baru, f, pid))
        _bersihkan(c, pid)
        if not jangkar and lama:  # seluruh wajah pindah: ini orang yang sama, namanya ikut
            c.execute("UPDATE person SET nama=? WHERE id=?", (lama, baru))
    return beri_nama(c, baru, nama) if nama and nama.strip() else baru


def sembunyikan(c, pid):
    with c:
        c.execute("UPDATE person SET tersembunyi=1 WHERE id=?", (pid,))


def _pusat(blob_list):
    V = np.frombuffer(b"".join(blob_list), np.float16).reshape(-1, 512).astype(np.float32)
    p = V.mean(0)
    return p / max(float(np.linalg.norm(p)), 1e-9)


def _pita(s):
    return "Sangat mirip" if s >= 0.60 else "Mirip" if s >= 0.50 else "Agak mirip"


def pusat_semua(c):
    """Pusat tiap orang yang punya foto terlihat, dari 20 wajah terbaiknya."""
    wajah = {}
    for p, e in c.execute("SELECT person_id, embedding FROM (SELECT f.person_id, f.embedding, "
                          "row_number() OVER (PARTITION BY f.person_id ORDER BY f.kualitas DESC) r FROM face f "
                          "JOIN photo ph ON ph.id=f.photo_id AND ph.status='ok' WHERE f.person_id IS NOT NULL) WHERE r <= 20"):
        wajah.setdefault(p, []).append(e)
    return {p: _pusat(e) for p, e in wajah.items()}


def saran(c, pid, pusat=None):
    """Orang lain yang paling mungkin sama. `pusat` dari `pusat_semua`, supaya tinjau tetap cepat."""
    pusat = pusat_semua(c) if pusat is None else pusat
    if pid not in pusat:
        return None
    lawan = set()
    for a, b in c.execute("SELECT f1.person_id, f2.person_id FROM batasan x JOIN face f1 ON f1.id=x.face_a "
                          "JOIN face f2 ON f2.id=x.face_b WHERE x.jenis='beda' AND (f1.person_id=? OR f2.person_id=?)",
                          (pid, pid)):
        lawan |= {a, b}
    sembunyi = {b[0] for b in c.execute("SELECT id FROM person WHERE tersembunyi=1")}
    calon = [p for p in pusat if p != pid and p not in lawan and p not in sembunyi]
    if not calon:
        return None
    skor = np.stack([pusat[p] for p in calon]) @ pusat[pid]
    for i in np.argsort(-skor):
        if skor[i] < 0.35:
            return None
        p = calon[int(i)]
        sefoto = c.execute("SELECT 1 FROM face a JOIN face b ON a.photo_id=b.photo_id WHERE a.person_id=? AND b.person_id=? LIMIT 1",
                           (pid, p)).fetchone()
        if not sefoto:  # dua wajah di satu foto bukan orang yang sama
            return {**info(c, p), "pita": _pita(float(skor[i]))}
    return None


def _wajah_baris(c, pid):
    return c.execute("SELECT f.id, ph.sha1, f.x1, f.y1, f.x2, f.y2, f.kualitas, f.embedding FROM face f "
                     "JOIN photo ph ON ph.id=f.photo_id WHERE f.person_id=? AND ph.status='ok' "
                     "ORDER BY f.kualitas DESC, f.id", (pid,)).fetchall()


def contoh(c, pid, n=12):
    """Wajah terbaik, ditambah yang paling tidak mirip supaya salah kelompok mudah terlihat."""
    b = _wajah_baris(c, pid)
    if len(b) > n:
        p = _pusat([x[7] for x in b])
        kemiripan = np.frombuffer(b"".join(x[7] for x in b), np.float16).reshape(-1, 512).astype(np.float32) @ p
        jauh = [int(i) for i in np.argsort(kemiripan)[:n // 3]]
        dekat = [i for i in range(len(b)) if i not in jauh][:n - len(jauh)]
        b = [b[i] for i in dekat + jauh]
    return [{"id": x[0], **_kotak(*x[1:6])} for x in b]


def wajah_orang(c, pid, batas=2000):
    return [{"id": x[0], **_kotak(*x[1:6])} for x in _wajah_baris(c, pid)[:batas]]
