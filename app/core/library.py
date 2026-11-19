import calendar
import ctypes
import os
from typing import NamedTuple


class Foto(NamedTuple):
    id: int
    source_id: int
    jalur_rel: str
    sha1: str
    lebar: int
    tinggi: int
    taken_at: int
    ukuran: int


def serial_volume(akar):
    """Nomor seri volume, kosong bila tidak bisa dibaca (mis. jalur jaringan)."""
    serial = ctypes.c_ulong()
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(akar), None, 0, ctypes.byref(serial), None, None, None, 0)
    return f"{serial.value:08X}" if ok else ""


def tambah_sumber(c, akar):
    akar = os.path.abspath(akar)
    huruf, sisa = os.path.splitdrive(akar)
    relatif = sisa.strip("\\/")
    serial = serial_volume(huruf + "\\")
    label = os.path.basename(akar) or huruf
    with c:
        c.execute("INSERT OR IGNORE INTO source(serial, akar_relatif, huruf_terakhir, label) VALUES (?,?,?,?)",
                  (serial, relatif, huruf, label))
    return c.execute("SELECT id FROM source WHERE serial=? AND akar_relatif=? AND huruf_terakhir=?",
                     (serial, relatif, huruf)).fetchone()[0]


def pindah_sumber(c, source_id, akar):
    """Arahkan sumber ke folder lain, mis. setelah folder diganti nama. Pindai berikutnya mencocokkan isinya."""
    akar = os.path.abspath(akar)
    huruf, sisa = os.path.splitdrive(akar)
    nilai = (serial_volume(huruf + "\\"), sisa.strip("\\/"), huruf)
    if c.execute("SELECT 1 FROM source WHERE serial=? AND akar_relatif=? AND huruf_terakhir=? AND id!=?", (*nilai, source_id)).fetchone():
        raise ValueError("Folder itu sudah ada di daftar.")
    with c:
        c.execute("UPDATE source SET serial=?, akar_relatif=?, huruf_terakhir=?, label=? WHERE id=?",
                  (*nilai, os.path.basename(akar) or huruf, source_id))


def hapus_sumber(c, source_id):
    with c:
        c.execute("DELETE FROM source WHERE id=?", (source_id,))


def _huruf_tersedia():
    bit = ctypes.windll.kernel32.GetLogicalDrives()
    return [f"{chr(65 + i)}:" for i in range(26) if bit >> i & 1]


def akar_sumber(c, source_id):
    """Letak folder sumber sekarang, walau huruf drive berubah. None bila tidak terhubung."""
    serial, relatif, huruf = c.execute("SELECT serial, akar_relatif, huruf_terakhir FROM source WHERE id=?",
                                       (source_id,)).fetchone()
    terakhir = os.path.join(huruf + "\\", relatif)
    if not serial:
        return terakhir if os.path.isdir(terakhir) else None
    if os.path.isdir(terakhir) and serial_volume(huruf + "\\") == serial:
        return terakhir
    for h in _huruf_tersedia():
        if h != huruf and serial_volume(h + "\\") == serial:
            calon = os.path.join(h + "\\", relatif)
            if os.path.isdir(calon):
                with c:
                    c.execute("UPDATE OR IGNORE source SET huruf_terakhir=? WHERE id=?", (h, source_id))
                return calon
    return None


def _where(saring):
    """Klausa WHERE dari saringan: orang, folder, sumber, bentuk, resolusi, tahun/bulan, daftar id foto."""
    klausa, arg = ["status='ok'"], []
    if not saring:
        return " AND ".join(klausa), arg
    for pid in saring.get("orang") or []:
        klausa.append("id IN (SELECT photo_id FROM face WHERE person_id=?)")
        arg.append(int(pid))
    panel = [int(p) for p in saring.get("orang_panel") or []]
    if panel and saring.get("salah_satu"):
        klausa.append(f"id IN (SELECT photo_id FROM face WHERE person_id IN ({','.join('?' * len(panel))}))")
        arg += panel
    else:
        for pid in panel:
            klausa.append("id IN (SELECT photo_id FROM face WHERE person_id=?)")
            arg.append(pid)
    folder = saring.get("folder")
    if folder:
        rel = folder["rel"]
        klausa.append("source_id=?")
        arg.append(int(folder["source"]))
        if rel:  # rel kosong = seluruh sumber
            klausa.append("substr(rel, 1, ?)=?")
            arg += [len(rel) + 1, rel + "/"]
    if saring.get("source"):
        klausa.append("source_id=?")
        arg.append(int(saring["source"]))
    bentuk = {"potret": "tinggi>lebar", "lanskap": "lebar>tinggi", "persegi": "lebar=tinggi"}.get(saring.get("orientasi"))
    if bentuk:
        klausa.append(bentuk)
    if saring.get("resolusi"):
        klausa.append("MAX(lebar, tinggi) >= ?")
        arg.append(int(saring["resolusi"]))
    tahun = int(saring.get("tahun") or 0)
    if tahun:
        bulan = int(saring.get("bulan") or 0)
        awal = calendar.timegm((tahun, bulan or 1, 1, 0, 0, 0))
        akhir = calendar.timegm((tahun + (bulan == 12 or not bulan), (bulan % 12 + 1) if bulan else 1, 1, 0, 0, 0))
        klausa.append("taken_at >= ? AND taken_at < ?")
        arg += [awal, akhir]
    foto = saring.get("foto")
    if foto is not None:
        klausa.append(f"id IN ({','.join('?' * len(foto))})")
        arg += [int(i) for i in foto]
    return " AND ".join(klausa), arg


def semua_foto(c, saring=None):
    klausa, arg = _where(saring)
    return [Foto(*b) for b in c.execute(
        f"SELECT id, source_id, rel, sha1, lebar, tinggi, taken_at, ukuran FROM photo WHERE {klausa} "
        "ORDER BY taken_at DESC, id DESC", arg)]


def foto_terbaru(c, saring, batas):
    klausa, arg = _where(saring)
    return [Foto(*b) for b in c.execute(
        f"SELECT id, source_id, rel, sha1, lebar, tinggi, taken_at, ukuran FROM photo WHERE {klausa} AND sha1 IS NOT NULL "
        "ORDER BY taken_at DESC, id DESC LIMIT ?", [*arg, batas])]


def tahun_foto(c):
    return [b[0] for b in c.execute("SELECT DISTINCT CAST(strftime('%Y', taken_at, 'unixepoch') AS INTEGER) FROM photo "
                                    "WHERE status='ok' ORDER BY 1 DESC")]


BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]


def koleksi(c, tahun, bulan, hari, batas=5):
    """Deretan kartu pembuka Galeri: terbaru, kenangan, orang terbanyak, folder terbesar. Tiap kartu punya sampul dan saringan."""
    hasil = []
    baru = c.execute("SELECT sha1, CAST(strftime('%Y', taken_at, 'unixepoch') AS INTEGER), CAST(strftime('%m', taken_at, 'unixepoch') AS INTEGER) "
                     "FROM photo WHERE status='ok' AND sha1 IS NOT NULL ORDER BY taken_at DESC, id DESC LIMIT 1").fetchone()
    if not baru:
        return hasil
    label = f"{BULAN[baru[2] - 1]} {baru[1]}"
    s = {"tahun": baru[1], "bulan": baru[2], "label": label}
    hasil.append({"judul": "Terbaru", "info": label, "jumlah": hitung(c, s), "sha1": baru[0], "saring": s})

    def kenangan(pola, judul):
        b = c.execute(f"SELECT id, sha1 FROM photo WHERE status='ok' AND sha1 IS NOT NULL AND strftime('{pola}', taken_at, 'unixepoch')=? "
                      "AND CAST(strftime('%Y', taken_at, 'unixepoch') AS INTEGER) < ? ORDER BY taken_at DESC, id DESC LIMIT 500",
                      (f"{bulan:02d}-{hari:02d}" if pola == "%m-%d" else f"{bulan:02d}", tahun)).fetchall()
        if b:
            hasil.append({"judul": judul, "info": f"{len(b)} foto", "jumlah": len(b), "sha1": b[0][1],
                          "saring": {"foto": [x[0] for x in b], "label": judul}})
        return bool(b)

    kenangan("%m-%d", "Kenangan hari ini") or kenangan("%m", "Kenangan bulan ini")

    for pid, nama, n, sha1 in c.execute(
            "SELECT p.id, p.nama, COUNT(DISTINCT f.photo_id), (SELECT ph.sha1 FROM face g JOIN photo ph ON ph.id=g.photo_id "
            "WHERE g.person_id=p.id AND ph.status='ok' ORDER BY ph.taken_at DESC LIMIT 1) "
            "FROM person p JOIN face f ON f.person_id=p.id JOIN photo ph ON ph.id=f.photo_id WHERE p.nama IS NOT NULL AND p.nama<>'' "
            "AND ph.status='ok' AND p.tersembunyi=0 GROUP BY p.id ORDER BY 3 DESC LIMIT 2"):
        hasil.append({"judul": nama, "info": f"{n} foto", "jumlah": n, "sha1": sha1, "saring": {"orang": [pid], "label": nama}})

    for sid, rel, n, sha1, _ in c.execute(
            "SELECT source_id, substr(rel, 1, instr(rel, '/') - 1) f, COUNT(*), sha1, MAX(taken_at) FROM photo "
            "WHERE status='ok' AND sha1 IS NOT NULL AND instr(rel, '/') > 0 GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 2"):
        hasil.append({"judul": rel, "info": f"{n} foto", "jumlah": n, "sha1": sha1, "saring": {"folder": {"source": sid, "rel": rel}, "label": rel}})
    return hasil[:batas]


def hitung(c, saring=None):
    klausa, arg = _where(saring)
    return c.execute(f"SELECT count(*) FROM photo WHERE {klausa}", arg).fetchone()[0]


def pohon_folder(c):
    """{(source, folder): {jumlah, sha1 foto terbaru, sampul (3 terbaru), anak}}; jumlah termasuk subfolder. Folder akar = ""."""
    pohon = {}
    for sid, rel, sha1 in c.execute("SELECT source_id, rel, sha1 FROM photo WHERE status='ok' AND sha1 IS NOT NULL "
                                    "ORDER BY taken_at DESC, id DESC"):
        bagian = rel.split("/")[:-1]
        induk = None
        for n in range(len(bagian) + 1):
            kunci = (sid, "/".join(bagian[:n]))
            node = pohon.setdefault(kunci, {"jumlah": 0, "sha1": sha1, "sampul": [], "anak": set()})
            node["jumlah"] += 1
            if len(node["sampul"]) < 3 and sha1 not in node["sampul"]:
                node["sampul"].append(sha1)
            if induk is not None:
                pohon[induk]["anak"].add(kunci[1])
            induk = kunci
    return pohon


def daftar_sumber(c):
    return c.execute(
        "SELECT s.id, s.label, s.huruf_terakhir, s.akar_relatif, s.terakhir_pindai, "
        "COALESCE(SUM(p.status='ok'),0), COALESCE(SUM(p.status='gagal'),0), COALESCE(SUM(p.status='hilang'),0) "
        "FROM source s LEFT JOIN photo p ON p.source_id=s.id GROUP BY s.id ORDER BY s.id").fetchall()
