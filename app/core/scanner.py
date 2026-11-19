"""Tahap A: temukan foto, baca sekali berurutan, dekode paralel, simpan metadata dan thumbnail."""
import calendar
import ctypes
import hashlib
import io
import os
import time
from collections import deque
from concurrent.futures import BrokenExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageOps

from core import library, thumbs

EXT_FOTO = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
FOLDER_LEWAT = {"$recycle.bin", "system volume information", "_rapikanalbum"}
BATCH = 100


@dataclass
class Ringkasan:
    baru: int = 0
    berubah: int = 0
    dipindah: int = 0
    gagal: int = 0
    hilang: int = 0
    dilewati: int = 0
    folder_tak_terbaca: int = 0
    galat_sistem: str = ""
    terputus: bool = False
    dibatalkan: bool = False


class GagalBaca(Exception):
    """Isi file memang tidak bisa dibaca sebagai foto; dicatat dan tidak dicoba lagi sampai file berubah."""


def _panjang(p):
    return p if p.startswith("\\\\") else "\\\\?\\" + os.path.abspath(p)


def temukan(akar):
    """Kembalikan ({rel: (ukuran, mtime_ns)}, jumlah dilewati, [folder relatif yang tak terbaca])."""
    dasar = _panjang(akar)
    potong = len(dasar.rstrip("\\")) + 1
    berkas, dilewati, tak_terbaca = {}, 0, []
    tumpuk = [dasar]
    while tumpuk:
        lokasi = tumpuk.pop()
        try:
            with os.scandir(lokasi) as it:
                for e in it:
                    if e.is_junction():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if not e.name.startswith(".") and e.name.lower() not in FOLDER_LEWAT:
                            tumpuk.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        if os.path.splitext(e.name)[1].lower() in EXT_FOTO:
                            s = e.stat()
                            berkas[e.path[potong:].replace("\\", "/")] = (s.st_size, s.st_mtime_ns)
                        else:
                            dilewati += 1
        except OSError:
            tak_terbaca.append(lokasi[potong:].replace("\\", "/"))
    return berkas, dilewati, tak_terbaca


def cocok_lokasi(c, source_id, akar):
    """(foto sumber ini yang ketemu di `akar` menurut nama dan ukuran, jumlah foto di `akar`)."""
    berkas, _, _ = temukan(akar)
    ada = {(rel.rsplit("/", 1)[-1].lower(), u) for rel, (u, _) in berkas.items()}
    kenal = sum((rel.rsplit("/", 1)[-1].lower(), u) in ada for rel, u in c.execute(
        "SELECT rel, ukuran FROM photo WHERE source_id=? AND status!='gagal'", (source_id,)))
    return kenal, len(berkas)


def _tanggal_exif(exif):
    for nilai in (exif.get_ifd(0x8769).get(36867), exif.get(306)):
        try:
            t = datetime.strptime(str(nilai).strip("\x00 ")[:19], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
        if 1970 <= t.year <= datetime.now().year + 1:
            return calendar.timegm(t.timetuple())
    return None


def siapkan_pillow():
    Image.MAX_IMAGE_PIXELS = None  # foto milik pemilik sendiri; panorama besar sah
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass


def olah(data, akar_thumb):
    """Dijalankan di proses pekerja. Galat dekode naik ke pemanggil."""
    siapkan_pillow()
    sha1 = hashlib.sha1(data).hexdigest()
    try:
        im = Image.open(io.BytesIO(data))
        lebar, tinggi = im.size
        exif = im.getexif()
        if exif.get(0x0112, 1) in (5, 6, 7, 8):
            lebar, tinggi = tinggi, lebar
        taken_at = _tanggal_exif(exif)
        im.draft("RGB", (1280, 1280))
        gambar = ImageOps.exif_transpose(im).convert("RGB")
    except MemoryError:
        raise
    except Exception as e:  # Pillow melempar banyak jenis galat untuk file rusak
        raise GagalBaca(repr(e)[:300]) from None
    thumbs.buat(gambar, akar_thumb, sha1)  # galat di sini soal disk, bukan soal foto
    return sha1, lebar, tinggi, taken_at


def _proses_rendah():
    # BELOW_NORMAL_PRIORITY_CLASS: antarmuka tetap lancar selama memindai
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)


def _dari_mtime(mtime_ns):
    try:
        return calendar.timegm(datetime.fromtimestamp(mtime_ns / 1e9).timetuple())
    except (OSError, OverflowError, ValueError):
        return 0


class Pemindai:
    def __init__(self, c, akar_thumb, pekerja=3, olah=olah):
        self.c, self.akar_thumb, self.pekerja, self.olah = c, akar_thumb, pekerja, olah

    def _baca(self, p):
        with open(_panjang(p), "rb") as f:
            return f.read()

    def _pool(self):
        return ProcessPoolExecutor(self.pekerja, initializer=_proses_rendah)

    def _sendiri(self, data):
        """Olah satu file di proses baru, untuk menemukan file yang mematikan pekerja."""
        p = ProcessPoolExecutor(1, initializer=_proses_rendah)
        try:
            return p.submit(self.olah, data, str(self.akar_thumb)).result()
        except BrokenExecutor:
            raise GagalBaca("proses pembaca berhenti pada file ini") from None
        finally:
            p.shutdown(wait=True, cancel_futures=True)

    def jalankan(self, source_id, batal=None, jeda=None, lapor=None):
        r = Ringkasan()
        c = self.c
        akar = library.akar_sumber(c, source_id)
        if akar is None:
            r.terputus = True
            return r
        berkas, r.dilewati, tak_terbaca = temukan(akar)
        if not os.path.isdir(akar):
            r.terputus = True
            return r
        r.folder_tak_terbaca = len(tak_terbaca)

        def terjangkau(rel):
            return not any(d == "" or rel == d or rel.startswith(d + "/") for d in tak_terbaca)

        lama = {b[0]: b[1:] for b in c.execute(
            "SELECT rel, id, ukuran, mtime_ns, status, sha1 FROM photo WHERE source_id=?", (source_id,))}
        tak_ada = {rel for rel in lama if rel not in berkas and terjangkau(rel)}

        kerja = []
        with c:
            for rel in sorted(berkas):
                u, m = berkas[rel]
                if rel not in lama or (lama[rel][1], lama[rel][2]) != (u, m):
                    kerja.append(rel)
                elif lama[rel][3] == "hilang":
                    c.execute("UPDATE photo SET status='ok' WHERE id=?", (lama[rel][0],))

        # Pindah folder tanpa membaca ulang: nama, ukuran, dan waktu ubah sama, dan hanya ada satu pasangan.
        # shortcut: isi tidak diperiksa; file lain yang kebetulan sama ketiganya akan dianggap foto yang sama.
        def kunci(rel, u, m):
            return rel.rsplit("/", 1)[-1].lower(), u, m

        pergi, datang = {}, {}
        for rel in tak_ada:
            if lama[rel][3] != "gagal" and lama[rel][4]:
                pergi.setdefault(kunci(rel, lama[rel][1], lama[rel][2]), []).append(rel)
        for rel in kerja:
            if rel not in lama:
                datang.setdefault(kunci(rel, *berkas[rel]), []).append(rel)
        langsung = {d[0]: pergi[k][0] for k, d in datang.items() if len(d) == 1 and len(pergi.get(k, ())) == 1}
        if langsung:
            with c:
                for baru, asal in langsung.items():
                    c.execute("UPDATE photo SET rel=?, status='ok' WHERE id=?", (baru, lama[asal][0]))
                    tak_ada.discard(asal)
            r.dipindah += len(langsung)
            kerja = [rel for rel in kerja if rel not in langsung]

        # Baris yang isinya mungkin berpindah: file hilang, atau jalur yang isinya berubah
        kandidat = {}
        for rel in tak_ada.union(k for k in kerja if k in lama):
            if lama[rel][3] != "gagal" and lama[rel][4]:
                kandidat.setdefault(lama[rel][4], []).append(rel)

        pool = self._pool() if kerja else None
        antre = deque()
        tunda = []
        selesai = 0
        komit = time.monotonic()

        def terima(rel, ambil):
            nonlocal selesai, komit
            u, m = berkas[rel]
            try:
                hasil = ambil()
            except BrokenExecutor:
                raise
            except GagalBaca as e:
                self._gagal(source_id, rel, u, m, str(e), lama, r)
            except Exception as e:  # disk penuh dan sejenisnya: foto tidak salah, dicoba lagi nanti
                r.gagal += 1
                r.galat_sistem = repr(e)[:300]
            else:
                self._simpan(source_id, rel, u, m, hasil, lama, kandidat, tunda, r)
            selesai += 1
            if time.monotonic() - komit >= 1:
                c.commit()
                komit = time.monotonic()
            if lapor and selesai % BATCH == 0:
                lapor(selesai, len(kerja))

        def pulihkan():
            nonlocal pool
            pool.shutdown(wait=False, cancel_futures=True)
            while antre:
                rel, data, _ = antre.popleft()
                terima(rel, lambda d=data: self._sendiri(d))
            pool = self._pool()

        def selesaikan_satu():
            rel, _, masa = antre[0]
            try:
                terima(rel, masa.result)
            except BrokenExecutor:
                pulihkan()
            else:
                antre.popleft()

        try:
            for rel in kerja:
                if jeda and jeda():
                    c.commit()  # jangan menahan kunci tulis selama dijeda
                    while jeda() and not (batal and batal.is_set()):
                        time.sleep(0.2)
                if batal and batal.is_set():
                    r.dibatalkan = True
                    break
                if len(antre) >= self.pekerja * 2:
                    selesaikan_satu()
                try:
                    data = self._baca(os.path.join(akar, rel))
                except OSError:
                    if not os.path.isdir(akar):
                        r.terputus = True
                        break
                    r.gagal += 1  # tidak disimpan: file terkunci dicoba lagi di pindai berikutnya
                    continue
                try:
                    antre.append((rel, data, pool.submit(self.olah, data, str(self.akar_thumb))))
                except BrokenExecutor:
                    antre.append((rel, data, None))
                    pulihkan()
            while antre:
                selesaikan_satu()
        finally:
            if pool:
                pool.shutdown(wait=True, cancel_futures=True)

        with c:
            if not (r.terputus or r.dibatalkan):
                self._terapkan(source_id, tunda, lama, kandidat, tak_ada, r)
                for rel in tak_ada:
                    if lama[rel][3] == "ok":
                        c.execute("UPDATE photo SET status='hilang' WHERE id=?", (lama[rel][0],))
                        r.hilang += 1
                    elif lama[rel][3] == "gagal":
                        c.execute("DELETE FROM photo WHERE id=?", (lama[rel][0],))
            c.execute("UPDATE source SET terakhir_pindai=? WHERE id=?", (int(time.time()), source_id))
        if lapor:
            lapor(selesai, len(kerja))
        return r

    def _nilai(self, m, hasil):
        sha1, lb, tg, tgl = hasil
        tanggal, sumber = (tgl, "exif") if tgl is not None else (_dari_mtime(m), "mtime")
        return sha1, lb, tg, tanggal, sumber

    def _simpan(self, source_id, rel, u, m, hasil, lama, kandidat, tunda, r):
        nilai = (u, m, *self._nilai(m, hasil))
        if rel in lama or nilai[2] in kandidat:
            tunda.append((rel, nilai))  # butuh gambaran utuh agar rantai ganti nama benar
            return
        self.c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, "
                       "sumber_tanggal, status) VALUES (?,?,?,?,?,?,?,?,?,'ok')", (source_id, rel, *nilai))
        r.baru += 1

    def _terapkan(self, source_id, tunda, lama, kandidat, tak_ada, r):
        """Cocokkan isi dengan SHA-1 lebih dulu, baru jalur, supaya id mengikuti fotonya."""
        c = self.c
        ubah = ("UPDATE photo SET rel=?, ukuran=?, mtime_ns=?, sha1=?, lebar=?, tinggi=?, taken_at=?, "
                "sumber_tanggal=?, status='ok', galat=NULL WHERE id=?")
        sisa, pindah = [], []
        pergi = set()
        for rel, nilai in tunda:
            if rel in lama and lama[rel][4] == nilai[2]:
                if rel in kandidat.get(nilai[2], []):
                    kandidat[nilai[2]].remove(rel)
                c.execute(ubah, (rel, *nilai, lama[rel][0]))
                r.berubah += 1
            else:
                sisa.append((rel, nilai))
        baru = []
        for rel, nilai in sisa:
            asal = kandidat.get(nilai[2])
            if asal:
                a = asal.pop()
                pergi.add(a)
                tak_ada.discard(a)
                pindah.append((rel, nilai, lama[a][0]))
            else:
                baru.append((rel, nilai))
        for _, _, i in pindah:
            c.execute("UPDATE photo SET rel=? WHERE id=?", (f"\\{i}", i))
        for rel, nilai in baru:
            if rel in lama and rel not in pergi:
                c.execute(ubah, (rel, *nilai, lama[rel][0]))
                self._lupakan_wajah(lama[rel][0])  # isi berbeda: wajah lamanya bukan milik foto ini
                r.berubah += 1
            else:
                c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, sha1, lebar, tinggi, taken_at, "
                          "sumber_tanggal, status) VALUES (?,?,?,?,?,?,?,?,?,'ok')", (source_id, rel, *nilai))
                r.baru += 1
        for rel, nilai, _ in pindah:
            if rel in lama and rel not in pergi:
                # Isi lama di jalur ini sudah tidak ada; barisnya disisihkan agar bisa ditemukan lagi lewat SHA-1
                c.execute("UPDATE photo SET rel=?, status='hilang' WHERE id=?", (f"\\{lama[rel][0]}", lama[rel][0]))
                r.hilang += 1
        for rel, nilai, i in pindah:
            c.execute(ubah, (rel, *nilai, i))
            r.dipindah += 1

    def _lupakan_wajah(self, photo_id):
        self.c.execute("DELETE FROM face WHERE photo_id=?", (photo_id,))
        self.c.execute("UPDATE photo SET wajah_model=NULL, wajah_galat=NULL WHERE id=?", (photo_id,))

    def _gagal(self, source_id, rel, u, m, pesan, lama, r):
        if rel in lama:
            self.c.execute("UPDATE photo SET ukuran=?, mtime_ns=?, status='gagal', galat=? WHERE id=?",
                           (u, m, pesan, lama[rel][0]))
            self._lupakan_wajah(lama[rel][0])
        else:
            self.c.execute("INSERT INTO photo(source_id, rel, ukuran, mtime_ns, taken_at, status, galat) "
                           "VALUES (?,?,?,?,?,'gagal',?)", (source_id, rel, u, m, _dari_mtime(m), pesan))
        r.gagal += 1
